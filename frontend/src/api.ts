// Thin client for the FastAPI backend (see backend/main.py).

export const API_BASE = "http://127.0.0.1:8000";

/** A row of data/yale_som_classes.json, exactly as the API returns it. */
export interface Course {
  "Course ID": string;
  "Course Number": string;
  "Course Title": string;
  "Course Description": string;
  "Course Category": string;
  "Course Type": string;
  "Course Session": string;
  "Course Session Start date": string;
  "Course Session End Date": string;
  Daytimes: string;
  "Timings Day": string;
  "Timings StartTime": string;
  "Timings EndTime": string;
  Room: string;
  Section: string;
  Units: string;
  "Faculty 1": string;
  "Faculty 1 Email": string;
  faculty_bio: string;
  Syllabus: string;
  "Old Syllabus": string;
  "Bid Or Permission": string;
  TermCode: string;
  Visible: string;
}

export interface CoursesResponse {
  count: number;
  courses: Course[];
}

export interface ChatResponse {
  reply: string;
  tools_used: string[];
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    throw new Error(`${res.status} ${res.statusText}`);
  }
  return (await res.json()) as T;
}

export async function fetchCourses(
  q?: string,
  signal?: AbortSignal,
): Promise<CoursesResponse> {
  const url = new URL("/api/courses", API_BASE);
  if (q && q.trim()) url.searchParams.set("q", q.trim());
  return asJson<CoursesResponse>(await fetch(url, { signal }));
}

export async function sendChat(
  message: string,
  signal?: AbortSignal,
): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/api/chat`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ message }),
    signal,
  });
  return asJson<ChatResponse>(res);
}

/** A course's meeting time, or a clear "not listed" — never invented. */
export function meetingTime(course: Course): string {
  const daytimes = course.Daytimes?.trim();
  if (daytimes) return daytimes.replace(/\s+/g, " ");
  const day = course["Timings Day"]?.trim();
  const start = course["Timings StartTime"]?.trim();
  const end = course["Timings EndTime"]?.trim();
  if (day && start) return `${day} ${start}${end ? `–${end}` : ""}`;
  return "No meeting time listed";
}

/** "Simonsohn, Uri" -> "Uri Simonsohn" */
export function displayFaculty(course: Course): string {
  const raw = course["Faculty 1"]?.trim();
  if (!raw) return "Instructor not listed";
  const [last, first] = raw.split(",").map((s) => s.trim());
  return first ? `${first} ${last}` : raw;
}
