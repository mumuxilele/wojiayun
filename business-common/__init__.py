# Common modules - Minimal version for server
# 先导入不依赖其他模块的类
from .order_status import OrderStatusTransition, OrderStatusValidator, OrderStatus
from .application_service import ApplicationService, application_service

# V50.0: MVC 架构重构 - 导出分层模块
from . import models
from . import repositories
from . import services

from .repositories import (
    ApplicationRepository,
    OrderRepository, 
    ProductRepository,
    UserRepository
)

from .services import (
    ApplicationService,
    OrderService,
    ProductService,
    UserService
)

# 再导入可能依赖配置的模块
from . import db
from . import config
from . import auth
from . import utils
from . import error_handler
from . import rate_limiter
from . import notification
from . import payment_service
from . import push_service
from . import user_settings_service
