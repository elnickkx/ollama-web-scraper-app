
# -*- coding: utf-8 -*-
"""

@Filename : application config
@created :  Dept 28 11:42 2020
@project: atlys-interview-assignment
@author : Nikkhil Butola
"""

import os

PROJECT_NAME = "scraping-event-handler"
SQLALCHEMY_DATABASE_URI = os.getenv("DATABASE_URL", "localhost:5432")
API_V1_STR = "/api/v1"
SECRET_KEY = "18f4e284c20f7efd72e85380a2ef7c71dca25a7a797ce7de093201a3bd3e83e8"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
STRIPE_HOST_DOMAIN = 'http://localhost:8000/api/v1'
SQLALCHEMY_DATABASE_NAME = os.getenv("DATABASE_NAME", "atlys_event_management")