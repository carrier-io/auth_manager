from typing import Union
from flask import request, make_response
from requests import Response
from pydantic import BaseModel


from ..rpc import add_subgroup
from ..models.group_pd import GroupRepresentation
from ..api.base import BaseResource


class SubGroup(BaseModel):
    parent: Union[GroupRepresentation, str]
    child: Union[GroupRepresentation, str]


class SubgroupAPI(BaseResource):
    @BaseResource.check_token
    def post(self, realm: str, **kwargs) -> Response:
        relationship = SubGroup.parse_obj(request.json)
        response = add_subgroup(
            group_url=self.settings['keycloak_urls']['group'],
            realm=realm,
            token=self.token,
            parent=relationship.parent,
            child=relationship.child,
            **kwargs
        )

        return make_response(response.dict(), response.status)
