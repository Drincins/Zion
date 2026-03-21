from pydantic import BaseModel


class AttachmentUploadResponse(BaseModel):
    """Public response for uploaded attachments stored in S3."""

    attachment_key: str
    attachment_url: str