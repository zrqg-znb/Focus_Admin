from typing import List, Optional

from ninja import Field, FilterSchema, ModelSchema, Schema

from common.fu_schema import FuFilters
from core.file_manager.file_manager_model import FileManager


class FileManagerSchemaOut(ModelSchema):
    parent_id: Optional[str] = Field(None, alias='parent_id')

    class Config:
        model = FileManager
        model_exclude = ('parent',)


class FileManagerSimpleSchemaOut(ModelSchema):
    parent_id: Optional[str] = Field(None, alias='parent_id')

    class Config:
        model = FileManager
        model_fields = ['id', 'name', 'type', 'path', 'size', 'url', 'storage_type', 'storage_path', 'sys_create_datetime']


class FileManagerFilters(FuFilters):
    parent_id: Optional[str] = Field(None, q='parent_id')
    type: Optional[str] = Field(None, q='type')
    name: Optional[str] = Field(None, q='name__icontains')
    storage_type: Optional[str] = Field(None, q='storage_type')
    is_public: Optional[bool] = Field(None, q='is_public')


class CreateFolderSchemaIn(Schema):
    name: str
    parent_id: Optional[str] = None


class MoveItemsSchemaIn(Schema):
    ids: List[str]
    target_folder_id: Optional[str] = None


class RenameItemSchemaIn(Schema):
    name: str


class BatchDeleteSchemaIn(Schema):
    ids: List[str]


class FileStorageConfigSchema(Schema):
    storage_type: str = Field('local')
    local_base_path: Optional[str] = None


class InitChunkUploadSchemaIn(Schema):
    filename: str
    total_size: int
    chunk_size: int = 5 * 1024 * 1024
    file_hash: Optional[str] = None
    parent_id: Optional[str] = None
    is_public: bool = False


class InitChunkUploadSchemaOut(Schema):
    upload_id: str
    chunk_size: int
    total_chunks: int
    uploaded_chunks: List[int]
    file_exists: bool
    file_id: Optional[str] = None


class UploadChunkSchemaOut(Schema):
    chunk_index: int
    uploaded: bool


class MergeChunksSchemaIn(Schema):
    upload_id: str


class ChunkUploadStatusSchemaOut(Schema):
    upload_id: str
    filename: str
    total_size: int
    total_chunks: int
    uploaded_chunks: List[int]
    completed: bool
