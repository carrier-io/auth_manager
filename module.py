#!/usr/bin/python3
# coding=utf-8

#   Copyright 2021 getcarrier.io
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#       http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.

""" Module """

import flask  # pylint: disable=E0401
from flask import session, make_response, request

from pylon.core.tools import log  # pylint: disable=E0611,E0401
from pylon.core.tools import module  # pylint: disable=E0611,E0401

from .api.base import BaseResource
from .api.group import GroupAPI
from .api.membership import MembershipAPI
from .api.subgroup import SubgroupAPI
from .api.user import UserAPI
from .models.token_pd import AuthCreds
from .rpc import get_users, get_groups, put_entity, post_entity, post_group, delete_entity, \
    add_users_to_groups, expel_users_from_groups, add_subgroup, create_user_representation
from .utils.tools import add_resource_to_api, get_token

from ..auth_root.utils.decorators import push_kwargs


class Module(module.ModuleModel):
    """ Pylon module """

    def __init__(self, context, descriptor):
        self.context = context
        self.descriptor = descriptor
        self.rpc_prefix = None
        #
        self.settings = self.descriptor.config

    def init(self):
        """ Init module """
        log.info('Initializing module auth_manager')
        root_settings = self.context.module_manager.modules["auth_root"].config

        self.rpc_prefix = root_settings['rpc_manager']['prefix']['manager']
        url_prefix = f'/{self.settings["endpoints"]["root"]}'

        BaseResource.set_settings(
            self.settings,
            rpc_prefix=self.rpc_prefix,
            rpc_prefix_root=root_settings['rpc_manager']['prefix']['root']
        )
        BaseResource.set_rpc_manager(self.context.rpc_manager)

        add_resource_to_api(self.context.api, UserAPI,
                            f'/user/<string:realm>',
                            f'/user/<string:realm>/<string:user_id>'
                            )
        add_resource_to_api(self.context.api, GroupAPI,
                            f'/group/<string:realm>',
                            f'/group/<string:realm>/<string:group_id>'
                            )
        add_resource_to_api(self.context.api, MembershipAPI,
                            f'/membership/<string:realm>',
                            methods=['PUT', 'POST']
                            )
        add_resource_to_api(self.context.api, SubgroupAPI,
                            f'/subgroup/<string:realm>',
                            methods=['POST']
                            )

        # rpc_manager
        # token
        self.context.rpc_manager.register_function(
            push_kwargs(
                url=self.settings['keycloak_urls']['token'],
                creds=AuthCreds(
                    username=self.settings['token_credentials']['username'],
                    password=self.settings['token_credentials']['password']
                )
            )(get_token),
            name=f'{self.rpc_prefix}get_token'
        )
        # get functions
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['user'])(get_users),
            name=f'{self.rpc_prefix}get_users')
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['group'])(get_groups),
            name=f'{self.rpc_prefix}get_groups')
        # put functions
        self.context.rpc_manager.register_function(put_entity, name=f'{self.rpc_prefix}put_entity')
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['user'])(put_entity),
            name=f'{self.rpc_prefix}put_user'
        )
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['group'])(put_entity),
            name=f'{self.rpc_prefix}put_group'
        )
        # post functions
        self.context.rpc_manager.register_function(post_entity, name=f'{self.rpc_prefix}post_entity')
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['user'])(post_entity),
            name=f'{self.rpc_prefix}post_user'
        )
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['group'])(post_group),
            name=f'{self.rpc_prefix}post_group'
        )
        # delete functions
        self.context.rpc_manager.register_function(delete_entity, name=f'{self.rpc_prefix}delete_entity')
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['user'])(delete_entity),
            name=f'{self.rpc_prefix}delete_user'
        )
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['group'])(delete_entity),
            name=f'{self.rpc_prefix}delete_group'
        )
        # group membership functions
        self.context.rpc_manager.register_function(
            push_kwargs(user_url=self.settings['keycloak_urls']['user'])(add_users_to_groups),
            name=f'{self.rpc_prefix}add_users_to_groups'
        )
        self.context.rpc_manager.register_function(
            push_kwargs(user_url=self.settings['keycloak_urls']['user'])(expel_users_from_groups),
            name=f'{self.rpc_prefix}expel_users_from_groups'
        )

        # subgroup functions
        self.context.rpc_manager.register_function(
            push_kwargs(base_url=self.settings['keycloak_urls']['group'])(add_subgroup),
            name=f'{self.rpc_prefix}add_subgroup'
        )
        self.context.rpc_manager.register_function(
            create_user_representation, name=f'{self.rpc_prefix}create_user_representation')
        # blueprint endpoints
        bp = self.descriptor.make_blueprint(
            url_prefix=url_prefix,
        )
        bp.add_url_rule('/clear_token', 'clear_token', self.clear_token, methods=['GET'])
        # Register in app
        self.context.app.register_blueprint(bp)

    def deinit(self):  # pylint: disable=R0201
        """ De-init module """
        log.info('De-initializing module auth_manager')

    @staticmethod
    def clear_token():
        # from flask import redirect
        for k in ('api_token', 'api_refresh_token'):
            try:
                del session[k]
            except KeyError:
                ...
        return make_response(None, 204)
