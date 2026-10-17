from pydantic import BaseModel, ConfigDict, Field

META_ID_PATTERN = r"^[0-9]{1,32}$"


class OAuthStartResponse(BaseModel):
    authorization_url: str


class OAuthAssetItem(BaseModel):
    external_account_id: str
    name: str
    page_id: str | None = None
    page_name: str | None = None


class OAuthAssetsResponse(BaseModel):
    provider: str
    assets: list[OAuthAssetItem]


class OAuthSelectRequest(BaseModel):
    token: str = Field(min_length=10, max_length=128)
    external_account_id: str = Field(pattern=META_ID_PATTERN)

    model_config = ConfigDict(extra="forbid")
