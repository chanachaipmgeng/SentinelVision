from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from fastapi import HTTPException, UploadFile
from ..models.member import Member
from ..utils.file_handler import save_uploaded_file
from uuid import UUID
from ..schemas.member_schema import MemberUpdate

async def get_users(db: AsyncSession):
    result = await db.execute(select(Member))
    return result.scalars().all()

async def get_user_by_id(id: UUID, db: AsyncSession):
    result = await db.execute(select(Member).where(Member.memberId == id))
    user = result.scalar_one_or_none()
    return user

async def create_user(user_data: dict, db: AsyncSession):
    user_dict = user_data.dict()  # แปลง Pydantic model เป็น dict
    password = user_dict.pop('password')  # ดึง password ออก
    new_user = Member(**user_dict)  # ใช้ dict ในการสร้าง Member instance
    new_user.hash_password(password)  # แฮชรหัสผ่าน
    db.add(new_user)
    await db.commit()
    await db.refresh(new_user)
    return new_user

async def update_user(id: UUID, user_data: MemberUpdate, db: AsyncSession):
    try:
        # Fetch the user
        result = await db.execute(select(Member).where(Member.memberId == id))
        member = result.scalar_one_or_none()

        if not member:
            raise HTTPException(status_code=404, detail="Member not found")

        # Update member fields (use is not None — role/status 0 are valid)
        if user_data.username is not None:
            member.username = user_data.username
        if user_data.password:
            member.hash_password(user_data.password)
        if user_data.firstName is not None:
            member.firstName = user_data.firstName
        if user_data.lastName is not None:
            member.lastName = user_data.lastName
        if user_data.email is not None:
            member.email = user_data.email
        if user_data.phoneNumber is not None:
            member.phoneNumber = user_data.phoneNumber
        if user_data.role is not None:
            member.role = user_data.role
        if user_data.status is not None:
            member.status = user_data.status
        if user_data.picture is not None:
            member.picture = user_data.picture
        if user_data.birthDate is not None:
            member.birthDate = user_data.birthDate
        if user_data.address is not None:
            member.address = user_data.address
        if user_data.emergencyContactName is not None:
            member.emergencyContactName = user_data.emergencyContactName
        if user_data.emergencyContactPhone is not None:
            member.emergencyContactPhone = user_data.emergencyContactPhone
        if user_data.attachmentUrls is not None:
            member.attachmentUrls = user_data.attachmentUrls

        # Save changes
        await db.commit()
        await db.refresh(member)

        return member
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def delete_user(memberId: UUID, db: AsyncSession):
    # Retrieve the member by ID
    member = await db.get(Member, memberId)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    # Delete the member instance
    await db.delete(member)
    await db.commit()

    return {
        "actionStatus": "Success",
        "message": "User deleted successfully",
        "statusCode": 200,
    }

