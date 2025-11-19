from functools import lru_cache
from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """
    Central configuration for the service.

    Values are read from environment variables prefixed with MR_*, e.g.:
      MR_TENANT_ID, MR_CLIENT_ID, MR_CLIENT_SECRET, MR_DRIVE_ID, MR_FOLDER_PATH
    """

    tenant_id: str = Field(..., description="Azure AD tenant ID")
    client_id: str = Field(..., description="Azure AD app registration client ID")
    client_secret: str = Field(..., description="Azure AD app registration client secret")

    # Target in SharePoint / OneDrive (Graph drive)
    drive_id: str = Field(..., description="Target drive ID in Microsoft Graph")
    folder_path: str = Field(
        default="MemoryRouter",
        description="Folder path under the drive root where entries are stored",
    )

    # Optional: site_id if you prefer addressing via site + drive instead of drive id
    site_id: str | None = Field(
        default=None, description="Optional SharePoint site ID (not required for basic drive usage)"
    )

    class Config:
        env_prefix = "MR_"
        env_file = ".env"


@lru_cache
def get_settings() -> Settings:
    return Settings()
