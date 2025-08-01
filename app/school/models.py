from sqlalchemy import Column, Integer, String, ForeignKey, UniqueConstraint
from sqlalchemy.orm import relationship, declarative_base

Base = declarative_base()

class Lesson(Base):
    __tablename__ = 'lessons'
    id = Column(Integer, primary_key=True)

    teacher_id = Column(Integer, ForeignKey('teachers.id'), nullable=False)
    class_id = Column(Integer, ForeignKey('classes.id'), nullable=False)
    subject_id = Column(Integer, ForeignKey('subjects.id'), nullable=False)

    hours = Column(Integer, nullable=False)

    teacher = relationship("Teacher", back_populates="lessons")
    school_class = relationship("SchoolClass", back_populates="lessons")
    subject = relationship("Subject", back_populates="lessons")

    __table_args__ = (
        UniqueConstraint('teacher_id', 'class_id', 'subject_id', name='_teacher_class_subject_uc'),
    )


class Teacher(Base):
    __tablename__ = 'teachers'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    lessons = relationship("Lesson", back_populates="teacher")


class SchoolClass(Base):
    __tablename__ = 'classes'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    lessons = relationship("Lesson", back_populates="school_class")


class Subject(Base):
    __tablename__ = 'subjects'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)

    lessons = relationship("Lesson", back_populates="subject")
