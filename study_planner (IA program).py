import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from datetime import datetime, date, timedelta
from pathlib import Path
import uuid

DB_FILE = Path(__file__).with_name("study_planner.db")
DAYS = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

def parse_date(value):
    return datetime.strptime(value.strip(), "%Y-%m-%d").date()

def parse_time(value):
    return datetime.strptime(value.strip(), "%H:%M").time()

def minutes_of(t):
    return t.hour * 60 + t.minute

def clock(minutes):
    return f"{minutes // 60:02d}:{minutes % 60:02d}"

class StudyPlanner:
    def __init__(self, root):
        self.root = root
        self.root.title("IB Study Planner")
        self.root.geometry("1100x720")
        self.root.minsize(900, 600)
        self.db = sqlite3.connect(DB_FILE)
        self.db.row_factory = sqlite3.Row
        self.create_tables()
        self.build_ui()
        self.load_profile()
        self.refresh_all()

    def create_tables(self):
        cur = self.db.cursor()
        cur.executescript("""
            CREATE TABLE IF NOT EXISTS profile (
                id INTEGER PRIMARY KEY CHECK(id=1),
                name TEXT NOT NULL DEFAULT 'Student',
                daily_limit INTEGER NOT NULL DEFAULT 180
            );
            INSERT OR IGNORE INTO profile(id, name, daily_limit)
            VALUES(1, 'Student', 180);

            CREATE TABLE IF NOT EXISTS subjects (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE
            );
            CREATE TABLE IF NOT EXISTS topics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                subject_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                exam_date TEXT NOT NULL,
                confidence INTEGER NOT NULL CHECK(confidence BETWEEN 1 AND 7),
                FOREIGN KEY(subject_id) REFERENCES subjects(id) ON DELETE CASCADE
            );
            CREATE TABLE IF NOT EXISTS constraints_table (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                day INTEGER NOT NULL CHECK(day BETWEEN 0 AND 6),
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                topic_id INTEGER NOT NULL,
                session_date TEXT NOT NULL,
                start_time TEXT NOT NULL,
                end_time TEXT NOT NULL,
                FOREIGN KEY(topic_id) REFERENCES topics(id) ON DELETE CASCADE
            );
        """)
        cur.execute("PRAGMA foreign_keys=ON")
        self.db.commit()

    def build_ui(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass
        style.configure("Title.TLabel", font=("Arial", 18, "bold"))
        style.configure("Treeview", rowheight=27)

        header = ttk.Frame(self.root, padding=(16, 12))
        header.pack(fill="x")
        ttk.Label(header, text="IB STUDY PLANNER", style="Title.TLabel").pack(side="left")
        ttk.Label(header, text="Plan smarter • prioritise weaker topics • protect your time",
                  foreground="#555").pack(side="right")

        self.tabs = ttk.Notebook(self.root)
        self.tabs.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        self.profile_tab = ttk.Frame(self.tabs, padding=14)
        self.subject_tab = ttk.Frame(self.tabs, padding=14)
        self.constraint_tab = ttk.Frame(self.tabs, padding=14)
        self.timetable_tab = ttk.Frame(self.tabs, padding=14)
        self.tabs.add(self.profile_tab, text="Profile")
        self.tabs.add(self.subject_tab, text="Subjects & Topics")
        self.tabs.add(self.constraint_tab, text="Fixed Constraints")
        self.tabs.add(self.timetable_tab, text="Weekly Timetable")

        self.build_profile_tab()
        self.build_subject_tab()
        self.build_constraint_tab()
        self.build_timetable_tab()

    def build_profile_tab(self):
        ttk.Label(self.profile_tab, text="Study profile", style="Title.TLabel").pack(anchor="w", pady=(0, 15))
        form = ttk.Frame(self.profile_tab)
        form.pack(anchor="w")
        ttk.Label(form, text="Your name").grid(row=0, column=0, sticky="w", padx=(0, 12), pady=8)
        self.name_var = tk.StringVar()
        ttk.Entry(form, textvariable=self.name_var, width=32).grid(row=0, column=1, pady=8)
        ttk.Label(form, text="Maximum study time per day (minutes)").grid(row=1, column=0, sticky="w", padx=(0, 12), pady=8)
        self.limit_var = tk.StringVar(value="180")
        ttk.Spinbox(form, from_=30, to=720, increment=15, textvariable=self.limit_var, width=10).grid(row=1, column=1, sticky="w", pady=8)
        ttk.Button(form, text="Save profile", command=self.save_profile).grid(row=2, column=1, sticky="w", pady=12)
        ttk.Separator(self.profile_tab).pack(fill="x", pady=18)
        ttk.Label(self.profile_tab, text="How the planner works", font=("Arial", 12, "bold")).pack(anchor="w")
        help_text = (
            "1. Add your IB subjects and the topics within each subject.\n"
            "2. Give each topic a confidence rating from 1 (least confident) to 7 (most confident), "
            "and enter its exam date.\n"
            "3. Add fixed commitments such as school and sports practices.\n"
            "4. Generate a timetable. The planner ranks topics using exam urgency and confidence, "
            "then places sessions in available time.\n\n"
            "Dates use YYYY-MM-DD and times use 24-hour HH:MM format. "
            "The generated timetable covers the next seven days."
        )
        ttk.Label(self.profile_tab, text=help_text, wraplength=850, justify="left").pack(anchor="w", pady=10)

    def build_subject_tab(self):
        ttk.Label(self.subject_tab, text="Subjects and topics", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        body = ttk.Frame(self.subject_tab)
        body.pack(fill="both", expand=True)

        left = ttk.LabelFrame(body, text="Subjects", padding=10)
        left.pack(side="left", fill="y", padx=(0, 12))
        self.subject_list = tk.Listbox(left, width=25, height=18, exportselection=False)
        self.subject_list.pack(fill="y", expand=True)
        self.subject_list.bind("<<ListboxSelect>>", self.on_subject_select)
        self.subject_name_var = tk.StringVar()
        ttk.Entry(left, textvariable=self.subject_name_var).pack(fill="x", pady=(10, 5))
        ttk.Button(left, text="Add subject", command=self.add_subject).pack(fill="x", pady=2)
        ttk.Button(left, text="Delete selected subject", command=self.delete_subject).pack(fill="x", pady=2)

        right = ttk.LabelFrame(body, text="Topics for selected subject", padding=10)
        right.pack(side="left", fill="both", expand=True)
        self.topic_tree = ttk.Treeview(right, columns=("topic", "exam", "confidence", "priority"),
                                       show="headings", height=12)
        for col, title, width in [
            ("topic", "Topic", 240), ("exam", "Exam date", 110),
            ("confidence", "Confidence / 7", 110), ("priority", "Priority", 90)
        ]:
            self.topic_tree.heading(col, text=title)
            self.topic_tree.column(col, width=width)
        self.topic_tree.pack(fill="both", expand=True)
        self.topic_tree.bind("<<TreeviewSelect>>", self.on_topic_select)

        form = ttk.Frame(right)
        form.pack(fill="x", pady=(12, 0))
        self.topic_name_var = tk.StringVar()
        self.exam_var = tk.StringVar(value=(date.today() + timedelta(days=30)).isoformat())
        self.conf_var = tk.StringVar(value="4")
        ttk.Label(form, text="Topic").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.topic_name_var, width=25).grid(row=1, column=0, padx=(0, 8), sticky="ew")
        ttk.Label(form, text="Exam date (YYYY-MM-DD)").grid(row=0, column=1, sticky="w")
        ttk.Entry(form, textvariable=self.exam_var, width=18).grid(row=1, column=1, padx=(0, 8), sticky="ew")
        ttk.Label(form, text="Confidence (1–7)").grid(row=0, column=2, sticky="w")
        ttk.Spinbox(form, from_=1, to=7, textvariable=self.conf_var, width=8).grid(row=1, column=2, padx=(0, 8), sticky="w")
        buttons = ttk.Frame(right)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Add topic", command=self.add_topic).pack(side="left", padx=(0, 6))
        ttk.Button(buttons, text="Update selected", command=self.update_topic).pack(side="left", padx=6)
        ttk.Button(buttons, text="Delete selected topic", command=self.delete_topic).pack(side="left", padx=6)
        self.selected_subject_id = None
        self.selected_topic_id = None

    def build_constraint_tab(self):
        ttk.Label(self.constraint_tab, text="Fixed commitments", style="Title.TLabel").pack(anchor="w", pady=(0, 10))
        ttk.Label(self.constraint_tab, text="Add periods when you cannot study, such as school, sport or other regular commitments.").pack(anchor="w", pady=(0, 12))
        self.constraint_tree = ttk.Treeview(self.constraint_tab, columns=("name", "day", "start", "end"), show="headings", height=13)
        for col, title, width in [("name", "Commitment", 300), ("day", "Day", 150), ("start", "Start", 120), ("end", "End", 120)]:
            self.constraint_tree.heading(col, text=title)
            self.constraint_tree.column(col, width=width)
        self.constraint_tree.pack(fill="both", expand=True)
        form = ttk.Frame(self.constraint_tab)
        form.pack(fill="x", pady=12)
        self.constraint_name_var = tk.StringVar()
        self.constraint_day_var = tk.StringVar(value="Monday")
        self.constraint_start_var = tk.StringVar(value="08:30")
        self.constraint_end_var = tk.StringVar(value="15:30")
        ttk.Label(form, text="Name").grid(row=0, column=0, sticky="w")
        ttk.Entry(form, textvariable=self.constraint_name_var, width=24).grid(row=1, column=0, padx=(0, 10))
        ttk.Label(form, text="Day").grid(row=0, column=1, sticky="w")
        ttk.Combobox(form, textvariable=self.constraint_day_var, values=DAYS, state="readonly", width=14).grid(row=1, column=1, padx=(0, 10))
        ttk.Label(form, text="Start (HH:MM)").grid(row=0, column=2, sticky="w")
        ttk.Entry(form, textvariable=self.constraint_start_var, width=12).grid(row=1, column=2, padx=(0, 10))
        ttk.Label(form, text="End (HH:MM)").grid(row=1, column=3, sticky="w")
        ttk.Entry(form, textvariable=self.constraint_end_var, width=12).grid(row=1, column=3, padx=(0, 10))
        ttk.Button(form, text="Add commitment", command=self.add_constraint).grid(row=1, column=4, padx=5)
        ttk.Button(form, text="Delete selected", command=self.delete_constraint).grid(row=1, column=5, padx=5)

    def build_timetable_tab(self):
        ttk.Label(self.timetable_tab, text="Weekly timetable", style="Title.TLabel").pack(anchor="w", pady=(0, 8))
        bar = ttk.Frame(self.timetable_tab)
        bar.pack(fill="x", pady=(0, 10))
        ttk.Button(bar, text="Generate / recalculate timetable", command=self.generate_timetable).pack(side="left")
        ttk.Button(bar, text="Export .ics", command=self.export_ics).pack(side="left", padx=8)
        self.timetable_note = ttk.Label(bar, text="Generate a timetable to view your next seven days.", foreground="#555")
        self.timetable_note.pack(side="left", padx=12)
        self.schedule_tree = ttk.Treeview(self.timetable_tab,
            columns=("day", "date", "start", "end", "subject", "topic"),
            show="headings", height=19)
        for col, title, width in [
            ("day", "Day", 105), ("date", "Date", 105), ("start", "Start", 75),
            ("end", "End", 75), ("subject", "Subject", 180), ("topic", "Topic", 300)
        ]:
            self.schedule_tree.heading(col, text=title)
            self.schedule_tree.column(col, width=width)
        self.schedule_tree.pack(fill="both", expand=True)

    def load_profile(self):
        row = self.db.execute("SELECT * FROM profile WHERE id=1").fetchone()
        self.name_var.set(row["name"])
        self.limit_var.set(str(row["daily_limit"]))

    def save_profile(self):
        try:
            name = self.name_var.get().strip() or "Student"
            limit = int(self.limit_var.get())
            if not 30 <= limit <= 720:
                raise ValueError
            self.db.execute("UPDATE profile SET name=?, daily_limit=? WHERE id=1", (name, limit))
            self.db.commit()
            messagebox.showinfo("Saved", "Your profile has been saved.")
        except ValueError:
            messagebox.showerror("Invalid input", "Daily study limit must be a whole number between 30 and 720 minutes.")

    def refresh_all(self):
        self.refresh_subjects()
        self.refresh_constraints()
        self.refresh_topics()

    def refresh_subjects(self):
        current = self.selected_subject_id
        self.subject_list.delete(0, tk.END)
        self.subject_ids = []
        rows = self.db.execute("SELECT * FROM subjects ORDER BY name").fetchall()
        for row in rows:
            self.subject_list.insert(tk.END, row["name"])
            self.subject_ids.append(row["id"])
        if current in self.subject_ids:
            index = self.subject_ids.index(current)
            self.subject_list.selection_set(index)
            self.selected_subject_id = current
        elif self.subject_ids:
            self.subject_list.selection_set(0)
            self.selected_subject_id = self.subject_ids[0]
        else:
            self.selected_subject_id = None

    def on_subject_select(self, _event=None):
        selection = self.subject_list.curselection()
        if selection:
            self.selected_subject_id = self.subject_ids[selection[0]]
            self.selected_topic_id = None
            self.refresh_topics()

    def add_subject(self):
        name = self.subject_name_var.get().strip()
        if not name:
            messagebox.showerror("Missing subject", "Enter a subject name.")
            return
        try:
            cur = self.db.execute("INSERT INTO subjects(name) VALUES(?)", (name,))
            self.db.commit()
            self.selected_subject_id = cur.lastrowid
            self.subject_name_var.set("")
            self.refresh_subjects()
            self.refresh_topics()
        except sqlite3.IntegrityError:
            messagebox.showerror("Duplicate subject", "That subject already exists.")

    def delete_subject(self):
        if not self.selected_subject_id:
            messagebox.showwarning("Select a subject", "Select a subject first.")
            return
        if messagebox.askyesno("Confirm deletion", "Delete this subject and all its topics?"):
            self.db.execute("DELETE FROM topics WHERE subject_id=?", (self.selected_subject_id,))
            self.db.execute("DELETE FROM subjects WHERE id=?", (self.selected_subject_id,))
            self.db.commit()
            self.selected_subject_id = None
            self.refresh_subjects()
            self.refresh_topics()

    def refresh_topics(self):
        if not hasattr(self, "topic_tree"):
            return
        for item in self.topic_tree.get_children():
            self.topic_tree.delete(item)
        if not self.selected_subject_id:
            return
        rows = self.db.execute("""
            SELECT t.*, s.name AS subject_name FROM topics t
            JOIN subjects s ON s.id=t.subject_id
            WHERE t.subject_id=? ORDER BY t.exam_date
        """, (self.selected_subject_id,)).fetchall()
        for row in rows:
            self.topic_tree.insert("", "end", iid=str(row["id"]),
                values=(row["name"], row["exam_date"], row["confidence"], f"{self.priority(row):.4f}"))

    def on_topic_select(self, _event=None):
        selected = self.topic_tree.selection()
        if not selected:
            return
        self.selected_topic_id = int(selected[0])
        row = self.db.execute("SELECT * FROM topics WHERE id=?", (self.selected_topic_id,)).fetchone()
        if row:
            self.topic_name_var.set(row["name"])
            self.exam_var.set(row["exam_date"])
            self.conf_var.set(str(row["confidence"]))

    def add_topic(self):
        if not self.selected_subject_id:
            messagebox.showwarning("Select a subject", "Add or select a subject first.")
            return
        try:
            name = self.topic_name_var.get().strip()
            exam = parse_date(self.exam_var.get()).isoformat()
            confidence = int(self.conf_var.get())
            if not name or not 1 <= confidence <= 7:
                raise ValueError
            self.db.execute("INSERT INTO topics(subject_id,name,exam_date,confidence) VALUES(?,?,?,?)",
                            (self.selected_subject_id, name, exam, confidence))
            self.db.commit()
            self.topic_name_var.set("")
            self.refresh_topics()
        except (ValueError, TypeError):
            messagebox.showerror("Invalid topic", "Enter a topic name, a valid date (YYYY-MM-DD), and confidence from 1 to 7.")

    def update_topic(self):
        if not self.selected_topic_id:
            messagebox.showwarning("Select a topic", "Select a topic to update.")
            return
        try:
            name = self.topic_name_var.get().strip()
            exam = parse_date(self.exam_var.get()).isoformat()
            confidence = int(self.conf_var.get())
            if not name or not 1 <= confidence <= 7:
                raise ValueError
            self.db.execute("UPDATE topics SET name=?, exam_date=?, confidence=? WHERE id=?",
                            (name, exam, confidence, self.selected_topic_id))
            self.db.commit()
            self.refresh_topics()
        except ValueError:
            messagebox.showerror("Invalid topic", "Enter a topic name, valid date and confidence from 1 to 7.")

    def delete_topic(self):
        if not self.selected_topic_id:
            messagebox.showwarning("Select a topic", "Select a topic to delete.")
            return
        self.db.execute("DELETE FROM topics WHERE id=?", (self.selected_topic_id,))
        self.db.commit()
        self.selected_topic_id = None
        self.topic_name_var.set("")
        self.refresh_topics()

    def refresh_constraints(self):
        for item in self.constraint_tree.get_children():
            self.constraint_tree.delete(item)
        rows = self.db.execute("SELECT * FROM constraints_table ORDER BY day,start_time").fetchall()
        for row in rows:
            self.constraint_tree.insert("", "end", iid=str(row["id"]),
                values=(row["name"], DAYS[row["day"]], row["start_time"], row["end_time"]))

    def add_constraint(self):
        try:
            name = self.constraint_name_var.get().strip()
            day = DAYS.index(self.constraint_day_var.get())
            start = parse_time(self.constraint_start_var.get())
            end = parse_time(self.constraint_end_var.get())
            if not name or minutes_of(start) >= minutes_of(end):
                raise ValueError
            self.db.execute("INSERT INTO constraints_table(name,day,start_time,end_time) VALUES(?,?,?,?)",
                (name, day, start.strftime("%H:%M"), end.strftime("%H:%M")))
            self.db.commit()
            self.constraint_name_var.set("")
            self.refresh_constraints()
        except (ValueError, IndexError):
            messagebox.showerror("Invalid commitment", "Enter a name, valid day and times (HH:MM). End must be after start.")

    def delete_constraint(self):
        selected = self.constraint_tree.selection()
        if not selected:
            messagebox.showwarning("Select a commitment", "Select a commitment to delete.")
            return
        self.db.execute("DELETE FROM constraints_table WHERE id=?", (int(selected[0]),))
        self.db.commit()
        self.refresh_constraints()

    def priority(self, topic):
        days = (parse_date(topic["exam_date"]) - date.today()).days
        # Urgency is capped to avoid division by zero and to handle past/today exams.
        urgency = 1.0 / max(days, 1)
        confidence_gap = 7 - int(topic["confidence"])
        # Both factors are normalised to a comparable scale.
        return (0.65 * min(urgency * 30, 1.0)) + (0.35 * (confidence_gap / 6.0))

    def get_available_intervals(self, day_index):
        # Default study window: 16:00–22:00. Fixed commitments are subtracted.
        intervals = [(16 * 60, 22 * 60)]
        rows = self.db.execute("SELECT start_time,end_time FROM constraints_table WHERE day=?",
                               (day_index,)).fetchall()
        for row in rows:
            block = (minutes_of(parse_time(row["start_time"])), minutes_of(parse_time(row["end_time"])))
            remaining = []
            for start, end in intervals:
                if block[1] <= start or block[0] >= end:
                    remaining.append((start, end))
                else:
                    if start < block[0]:
                        remaining.append((start, block[0]))
                    if block[1] < end:
                        remaining.append((block[1], end))
            intervals = remaining
        return sorted(intervals)

    def generate_timetable(self):
        try:
            self.save_profile_silently()
            limit = int(self.limit_var.get())
            if not 30 <= limit <= 720:
                raise ValueError
        except ValueError:
            messagebox.showerror("Invalid limit", "Save a daily study limit between 30 and 720 minutes first.")
            return

        topics = self.db.execute("""
            SELECT t.*, s.name AS subject_name FROM topics t
            JOIN subjects s ON s.id=t.subject_id
        """).fetchall()
        if not topics:
            messagebox.showwarning("No topics", "Add subjects and topics before generating a timetable.")
            return

        ranked = sorted(topics, key=self.priority, reverse=True)
        # Replace the previous generated week rather than making duplicate sessions.
        self.db.execute("DELETE FROM sessions")
        scheduled = []
        start_date = date.today()
        for offset in range(7):
            current = start_date + timedelta(days=offset)
            day_index = current.weekday()
            intervals = self.get_available_intervals(day_index)
            minutes_used = 0
            for interval_start, interval_end in intervals:
                cursor = interval_start
                while cursor + 45 <= interval_end and minutes_used + 45 <= limit:
                    eligible = [t for t in ranked if parse_date(t["exam_date"]) >= current]
                    if not eligible:
                        eligible = ranked
                    topic = eligible[(len(scheduled)) % len(eligible)]
                    session = {
                        "topic_id": topic["id"], "date": current.isoformat(),
                        "start": clock(cursor), "end": clock(cursor + 45),
                        "subject": topic["subject_name"], "topic": topic["name"],
                        "day": DAYS[day_index]
                    }
                    scheduled.append(session)
                    self.db.execute("INSERT INTO sessions(topic_id,session_date,start_time,end_time) VALUES(?,?,?,?)",
                        (session["topic_id"], session["date"], session["start"], session["end"]))
                    cursor += 45
                    minutes_used += 45
                if minutes_used + 45 > limit:
                    break

        self.db.commit()
        for item in self.schedule_tree.get_children():
            self.schedule_tree.delete(item)
        for i, s in enumerate(scheduled):
            self.schedule_tree.insert("", "end", iid=str(i),
                values=(s["day"], s["date"], s["start"], s["end"], s["subject"], s["topic"]))
        self.timetable_note.config(text=f"{len(scheduled)} sessions generated • 45 minutes each")
        if not scheduled:
            messagebox.showinfo("No sessions", "No suitable study slots were available in the default study window.")

    def save_profile_silently(self):
        name = self.name_var.get().strip() or "Student"
        limit = int(self.limit_var.get())
        self.db.execute("UPDATE profile SET name=?, daily_limit=? WHERE id=1", (name, limit))
        self.db.commit()

    def export_ics(self):
        rows = self.db.execute("""
            SELECT se.*, t.name AS topic_name, s.name AS subject_name
            FROM sessions se JOIN topics t ON t.id=se.topic_id
            JOIN subjects s ON s.id=t.subject_id
            ORDER BY se.session_date,se.start_time
        """).fetchall()
        if not rows:
            messagebox.showwarning("No timetable", "Generate a timetable before exporting.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".ics",
            filetypes=[("iCalendar files", "*.ics")], initialfile="study_timetable.ics")
        if not path:
            return

        def escape(text):
            return str(text).replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")

        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//IB Study Planner//EN", "CALSCALE:GREGORIAN"]
        for row in rows:
            start = datetime.combine(parse_date(row["session_date"]), parse_time(row["start_time"]))
            end = datetime.combine(parse_date(row["session_date"]), parse_time(row["end_time"]))
            lines.extend([
                "BEGIN:VEVENT",
                f"UID:{uuid.uuid4()}@ib-study-planner",
                f"DTSTAMP:{datetime.utcnow().strftime('%Y%m%dT%H%M%SZ')}",
                f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
                f"DTEND:{end.strftime('%Y%m%dT%H%M%S')}",
                f"SUMMARY:{escape(row['subject_name'] + ' - ' + row['topic_name'])}",
                "END:VEVENT"
            ])
        lines.append("END:VCALENDAR")
        Path(path).write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
        messagebox.showinfo("Export complete", f"Calendar exported successfully to:\n{path}")

    def close(self):
        self.db.close()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = StudyPlanner(root)
    root.protocol("WM_DELETE_WINDOW", app.close)
    root.mainloop()

if __name__ == "__main__":
    main()
