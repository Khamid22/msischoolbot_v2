export type Student = {
  id: string;
  name: string;
  course: string;
  group: string;
  rating: number;
  attendance: number;
  status: "active" | "inactive";
  avatarColor: string;
};

export type Teacher = {
  id: string;
  name: string;
  subject: string;
  groups: number;
  email: string;
};

export type Resource = {
  id: string;
  title: string;
  category: string;
  type: "PDF" | "Video" | "Link" | "Doc";
  uploaded: string;
  views: number;
};

export type ChatThread = {
  id: string;
  studentName: string;
  studentId: string;
  lastMessage: string;
  time: string;
  unread: number;
};

const colors = ["#6366f1", "#10b981", "#f59e0b", "#ef4444", "#8b5cf6", "#06b6d4", "#ec4899"];
const courses = ["AI & Data Science", "Web Development", "Cybersecurity", "Mobile Dev", "DevOps"];
const groups = ["MSI-101", "MSI-102", "MSI-201", "MSI-202", "MSI-301"];

export const students: Student[] = Array.from({ length: 24 }).map((_, i) => ({
  id: `MSI${String(20451 + i).padStart(5, "0")}`,
  name: [
    "Aiganym Nurlanova","Daulet Serikov","Madina Aliyeva","Timur Bekov","Sabina Yerlanova",
    "Arman Kuanysh","Dilnaz Omarova","Bekzat Toleu","Aizhan Suleimen","Nurlan Asylbek",
    "Adina Karim","Yerlan Daulet","Zarina Bek","Olzhas Tursyn","Kamila Asem",
    "Rashid Nurpeis","Aruzhan Sat","Aibek Zhumagali","Symbat Erlan","Dias Karim",
    "Aliya Tolep","Ruslan Aman","Zhansaya Olzhas","Bauyrzhan Sat",
  ][i],
  course: courses[i % courses.length],
  group: groups[i % groups.length],
  rating: Math.round((60 + Math.random() * 40) * 10) / 10,
  attendance: Math.round(70 + Math.random() * 30),
  status: Math.random() > 0.15 ? "active" : "inactive",
  avatarColor: colors[i % colors.length],
}));

export const teachers: Teacher[] = [
  { id: "T-01", name: "Dr. Aibek Nurtas", subject: "Machine Learning", groups: 4, email: "a.nurtas@msi.edu" },
  { id: "T-02", name: "Aigerim Smagul", subject: "Frontend Engineering", groups: 3, email: "a.smagul@msi.edu" },
  { id: "T-03", name: "Marat Yessenov", subject: "Network Security", groups: 2, email: "m.yessenov@msi.edu" },
  { id: "T-04", name: "Saltanat Bek", subject: "iOS Development", groups: 2, email: "s.bek@msi.edu" },
  { id: "T-05", name: "Daniyar Omar", subject: "Cloud & DevOps", groups: 3, email: "d.omar@msi.edu" },
];

export const resources: Resource[] = [
  { id: "R1", title: "Intro to Neural Networks", category: "AI & Data Science", type: "PDF", uploaded: "2 days ago", views: 142 },
  { id: "R2", title: "React Hooks Deep Dive", category: "Web Development", type: "Video", uploaded: "5 days ago", views: 318 },
  { id: "R3", title: "OWASP Top 10 — 2025", category: "Cybersecurity", type: "Link", uploaded: "1 week ago", views: 87 },
  { id: "R4", title: "SwiftUI Layout Guide", category: "Mobile Dev", type: "Doc", uploaded: "2 weeks ago", views: 56 },
  { id: "R5", title: "Kubernetes for Beginners", category: "DevOps", type: "Video", uploaded: "3 weeks ago", views: 201 },
  { id: "R6", title: "Pandas Cheat Sheet", category: "AI & Data Science", type: "PDF", uploaded: "1 month ago", views: 410 },
];

export const chats: ChatThread[] = students.slice(0, 8).map((s, i) => ({
  id: `C${i}`,
  studentName: s.name,
  studentId: s.id,
  lastMessage: [
    "When is the next assignment due?",
    "Thanks for the feedback!",
    "Can I get help with task 3?",
    "I uploaded my project.",
    "Please review my code.",
    "Will there be a retake?",
    "Got it, thank you.",
    "Is the lecture recorded?",
  ][i],
  time: ["2m", "12m", "1h", "3h", "5h", "yesterday", "2d", "3d"][i],
  unread: [2, 0, 1, 0, 3, 0, 0, 0][i],
}));

export const enrollmentTrend = [
  { month: "Jan", students: 180 },
  { month: "Feb", students: 195 },
  { month: "Mar", students: 220 },
  { month: "Apr", students: 245 },
  { month: "May", students: 268 },
  { month: "Jun", students: 290 },
  { month: "Jul", students: 312 },
  { month: "Aug", students: 340 },
];

export const courseDistribution = courses.map((c, i) => ({
  course: c,
  students: 40 + i * 15 + Math.floor(Math.random() * 20),
}));

export const activityWeek = [
  { day: "Mon", messages: 120, logins: 88 },
  { day: "Tue", messages: 145, logins: 102 },
  { day: "Wed", messages: 168, logins: 121 },
  { day: "Thu", messages: 132, logins: 95 },
  { day: "Fri", messages: 190, logins: 140 },
  { day: "Sat", messages: 78, logins: 45 },
  { day: "Sun", messages: 52, logins: 30 },
];
