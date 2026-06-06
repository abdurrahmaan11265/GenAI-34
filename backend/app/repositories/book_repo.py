from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.models.book import Book, GraphBuildJob, GraphVersion, UserBook

class BookRepository:
    def __init__(self, session: AsyncSession):
        self.session = session

    async def create_book(self, book: Book) -> Book:
        self.session.add(book)
        await self.session.flush()
        return book

    async def create_job(self, job: GraphBuildJob) -> GraphBuildJob:
        self.session.add(job)
        await self.session.flush()
        return job

    async def get_job_by_id(self, job_id: str) -> GraphBuildJob | None:
        result = await self.session.execute(select(GraphBuildJob).where(GraphBuildJob.id == job_id))
        return result.scalars().first()

    async def get_latest_job_for_book(self, book_id: str) -> GraphBuildJob | None:
        result = await self.session.execute(
            select(GraphBuildJob)
            .where(GraphBuildJob.book_id == book_id)
            .order_by(GraphBuildJob.created_at.desc())
        )
        return result.scalars().first()

    async def create_version(self, version: GraphVersion) -> GraphVersion:
        self.session.add(version)
        await self.session.flush()
        return version

    async def create_user_book(self, user_book: UserBook) -> UserBook:
        self.session.add(user_book)
        await self.session.flush()
        return user_book

    async def get_books_by_user(self, user_id: str):
        # We join UserBook to Book
        stmt = select(Book).join(UserBook).where(UserBook.user_id == user_id)
        result = await self.session.execute(stmt)
        return result.scalars().all()

    async def get_book_by_id(self, book_id: str) -> Book | None:
        result = await self.session.execute(select(Book).where(Book.id == book_id))
        return result.scalars().first()

    async def get_user_book(self, user_id: str, book_id: str) -> UserBook | None:
        result = await self.session.execute(
            select(UserBook).where(UserBook.user_id == user_id, UserBook.book_id == book_id)
        )
        return result.scalars().first()

    async def delete_user_book(self, user_book: UserBook):
        await self.session.delete(user_book)
        await self.session.flush()

    async def delete_book(self, book: Book):
        await self.session.delete(book)
        await self.session.flush()
