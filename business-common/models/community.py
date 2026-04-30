"""
Community 社区增值服务实体
"""
from .base_model import BaseModel


class CommunityService(BaseModel):
    TABLE_NAME = 'ts_community_service'
    PRIMARY_KEY = 'id'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.category_id = kwargs.get('category_id', 0)
        self.name = kwargs.get('name', '')
        self.image = kwargs.get('image')
        self.price = float(kwargs.get('price', 0))
        self.price_unit = kwargs.get('price_unit')
        self.description = kwargs.get('description')
        self.contact_phone = kwargs.get('contact_phone')
        self.contact_name = kwargs.get('contact_name')
        self.status = int(kwargs.get('status', 1))
        self.sort_order = int(kwargs.get('sort_order', 0))
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid,
            'category_id': self.category_id, 'name': self.name,
            'image': self.image, 'price': self.price,
            'price_unit': self.price_unit,
            'description': self.description,
            'contact_phone': self.contact_phone,
            'contact_name': self.contact_name,
            'status': self.status, 'sort_order': self.sort_order,
            'created_at': str(self.created_at) if self.created_at else None,
        }


class CommunityActivity(BaseModel):
    TABLE_NAME = 'ts_community_activity'
    PRIMARY_KEY = 'id'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.title = kwargs.get('title', '')
        self.cover = kwargs.get('cover')
        self.content = kwargs.get('content')
        self.activity_type = kwargs.get('activity_type', 'event')
        self.start_time = kwargs.get('start_time')
        self.end_time = kwargs.get('end_time')
        self.location = kwargs.get('location')
        self.max_participants = int(kwargs.get('max_participants', 0))
        self.current_participants = int(kwargs.get('current_participants', 0))
        self.status = int(kwargs.get('status', 1))
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid, 'title': self.title,
            'cover': self.cover, 'content': self.content,
            'activity_type': self.activity_type,
            'start_time': str(self.start_time) if self.start_time else None,
            'end_time': str(self.end_time) if self.end_time else None,
            'location': self.location,
            'max_participants': self.max_participants,
            'current_participants': self.current_participants,
            'status': self.status,
            'created_at': str(self.created_at) if self.created_at else None,
        }


class CommunityPost(BaseModel):
    TABLE_NAME = 'ts_community_post'
    PRIMARY_KEY = 'id'

    TYPE_IDLE = 'idle'
    TYPE_HELP = 'help'
    TYPE_INFO = 'info'

    def __init__(self, **kwargs):
        self.id = kwargs.get('id', 0)
        self.fid = kwargs.get('fid')
        self.user_id = kwargs.get('user_id', '')
        self.user_name = kwargs.get('user_name')
        self.user_avatar = kwargs.get('user_avatar')
        self.type = kwargs.get('type', self.TYPE_IDLE)
        self.title = kwargs.get('title', '')
        self.content = kwargs.get('content')
        self.images = kwargs.get('images')
        self.price = float(kwargs.get('price', 0)) if kwargs.get('price') else None
        self.contact_info = kwargs.get('contact_info')
        self.view_count = int(kwargs.get('view_count', 0))
        self.like_count = int(kwargs.get('like_count', 0))
        self.comment_count = int(kwargs.get('comment_count', 0))
        self.status = int(kwargs.get('status', 1))
        self.ec_id = kwargs.get('ec_id')
        self.project_id = kwargs.get('project_id')
        self.deleted = int(kwargs.get('deleted', 0))
        self.created_at = kwargs.get('created_at')
        self.updated_at = kwargs.get('updated_at')
        super().__init__(**kwargs)

    def to_dict(self):
        return {
            'id': self.id, 'fid': self.fid,
            'user_id': self.user_id, 'user_name': self.user_name,
            'user_avatar': self.user_avatar, 'type': self.type,
            'title': self.title, 'content': self.content,
            'images': self.images, 'price': self.price,
            'contact_info': self.contact_info,
            'view_count': self.view_count,
            'like_count': self.like_count,
            'comment_count': self.comment_count,
            'status': self.status,
            'created_at': str(self.created_at) if self.created_at else None,
        }
