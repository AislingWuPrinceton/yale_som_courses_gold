import { useState } from "react";
import { displayFaculty, meetingTime, type Course } from "../api";
import { ClockIcon, PersonIcon, PinIcon } from "./icons";

interface Props {
  course: Course;
}

export default function CourseCard({ course }: Props) {
  const [open, setOpen] = useState(false);

  const time = meetingTime(course);
  const timeListed = time !== "No meeting time listed";
  const room = course.Room?.trim();
  const units = course.Units?.trim();
  const category = course["Course Category"]?.trim();
  const description = course["Course Description"]?.trim();
  const syllabus = course.Syllabus?.trim() || course["Old Syllabus"]?.trim();

  return (
    <article className="card">
      <div className="card-top">
        <span className="course-number">
          {course["Course Number"] || "—"}
          {course.Section ? ` · ${course.Section}` : ""}
        </span>
        {category && <span className="chip">{category}</span>}
      </div>

      <h3>{course["Course Title"] || "Untitled course"}</h3>

      <div className="meta">
        <span className="meta-row">
          <PersonIcon />
          {displayFaculty(course)}
        </span>
        <span className={`meta-row${timeListed ? "" : " dim"}`}>
          <ClockIcon />
          {time}
        </span>
        {room && (
          <span className="meta-row">
            <PinIcon />
            {room}
            {units ? ` · ${units} units` : ""}
          </span>
        )}
      </div>

      {description && (
        <p className={`desc${open ? "" : " clamped"}`}>{description}</p>
      )}

      <div className="card-actions">
        {description && (
          <button
            type="button"
            className="link-btn"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
          >
            {open ? "Show less" : "Read more"}
          </button>
        )}
        {syllabus && (
          <a
            className="syllabus"
            href={syllabus}
            target="_blank"
            rel="noreferrer"
          >
            Syllabus ↗
          </a>
        )}
      </div>
    </article>
  );
}
