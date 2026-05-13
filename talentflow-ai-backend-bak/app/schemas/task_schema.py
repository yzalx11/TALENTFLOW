from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
from sqlalchemy import Column
from sqlalchemy.dialects.mysql import JSON as MySQLJSON


# 基础用户模型 

class UserBase(BaseModel):
    id: int
    username: str
    class Config:
        from_attributes = True

class TaskBase(BaseModel):
    '''
    
    '''
    title: str = Field(..., description="任务标题")
    description: Optional[str] = Field(None, description="任务详细描述")

    # 对应数据库新增字段
    category: str = Field(..., description="分类如前端、后端")
    price: int = Field(..., description="金额")
    duration: Optional[int] = Field(default=0, description="工期描述")

    difficulty: Optional[str] = Field(default=None, description="难度等级")
    skills: Optional[List[str]] = None
    taken_by: Optional[int] = None
    status: Optional[int] = Field(default=0, description="任务状态: 0-待审核, 1-进行中, 2-已暂停, 3-已完成")

  
class TaskCreate(TaskBase):
    pass
        
class TaskUpdate(BaseModel):
    """
    更新任务时的模型 
    """
    title: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    price: Optional[int] = None
    duration: Optional[int] = None
    skills: Optional[List[str]] = None
    status: Optional[int] = None

class TaskOut(TaskBase):
    '''
    返回给前端的任务模型
    '''
    id:int
    created_at:datetime
    
    class Config:
        from_attributes = True