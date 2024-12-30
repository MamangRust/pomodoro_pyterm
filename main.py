import curses
import sys
import time
import csv
import os
import pandas as pd
import matplotlib.pyplot as plt
from datetime import datetime
import threading
import plyer
from typing import Optional, List, Dict, Any


class TimerThread(threading.Thread):
    def __init__(self, duration: int, callback):
        super().__init__()
        self.duration = duration * 60  # convert to seconds
        self.callback = callback
        self.is_running = True
        self._stop_event = threading.Event()

    def run(self):
        remaining = self.duration
        while remaining > 0 and not self._stop_event.is_set():
            self.callback(remaining)
            time.sleep(1)
            remaining -= 1

        if not self._stop_event.is_set():
            self.callback(0)  # Final update

    def stop(self):
        self._stop_event.set()


class PomodoroApp:
    def __init__(self, stdscreen):
        self.screen = stdscreen
        self.tasks: List[Dict[str, Any]] = []
        self.current_timer: Optional[TimerThread] = None
        self.current_date = datetime.now().date()
        
        # Colors
        curses.start_color()
        curses.init_pair(1, curses.COLOR_BLUE, curses.COLOR_BLACK)
        curses.init_pair(2, curses.COLOR_GREEN, curses.COLOR_BLACK)
        curses.init_pair(3, curses.COLOR_RED, curses.COLOR_BLACK)
        
        # Initialize windows
        self.setup_windows()
        
        # Menu options
        self.menu_options = [
            "Add Task",
            "Start Timer",
            "Pause Timer",
            "Stop Timer",
            "View Tasks",
            "Visualize Data",
            "Exit"
        ]
        self.current_option = 0
        
        # Programming languages
        self.languages = ["Python", "Golang", "Java", "Rust"]
        self.current_language = 0

    def setup_windows(self):
        height, width = self.screen.getmaxyx()
        
        # Timer window (top)
        self.timer_win = curses.newwin(3, width-2, 1, 1)
        self.timer_win.box()
        
        # Menu window (middle)
        self.menu_win = curses.newwin(10, width-2, 4, 1)
        self.menu_win.box()
        
        # Task window (bottom)
        self.task_win = curses.newwin(height-15, width-2, 14, 1)
        self.task_win.box()
        
        # Refresh all windows
        self.screen.refresh()
        self.timer_win.refresh()
        self.menu_win.refresh()
        self.task_win.refresh()

    def display_timer(self, remaining: int):
        minutes = remaining // 60
        seconds = remaining % 60
        self.timer_win.clear()
        self.timer_win.box()
        self.timer_win.addstr(1, 2, f"Time Remaining: {minutes:02d}:{seconds:02d}")
        self.timer_win.refresh()

    def display_menu(self):
        self.menu_win.clear()
        self.menu_win.box()
        
        for idx, option in enumerate(self.menu_options):
            x = 2
            y = idx + 1
            if idx == self.current_option:
                self.menu_win.attron(curses.color_pair(1) | curses.A_BOLD)
                self.menu_win.addstr(y, x, f"> {option}")
                self.menu_win.attroff(curses.color_pair(1) | curses.A_BOLD)
            else:
                self.menu_win.addstr(y, x, f"  {option}")
        
        self.menu_win.refresh()

    def display_tasks(self):
        self.task_win.clear()
        self.task_win.box()
        
        if not self.tasks:
            self.task_win.addstr(1, 2, "No tasks yet")
        else:
            for idx, task in enumerate(self.tasks):
                if idx >= self.task_win.getmaxyx()[0] - 2:  # Prevent overflow
                    break
                task_str = f"{task['title']} | {task['duration']}min | {task['language']} | {task['status']}"
                self.task_win.addstr(idx + 1, 2, task_str[:self.task_win.getmaxyx()[1]-4])
        
        self.task_win.refresh()

    def get_string_input(self, prompt: str) -> str:
        curses.echo()
        self.screen.addstr(self.screen.getmaxyx()[0]-1, 0, prompt)
        self.screen.clrtoeol()
        self.screen.refresh()
        input_str = self.screen.getstr().decode('utf-8')
        curses.noecho()
        return input_str

    def add_task(self):
        title = self.get_string_input("Enter task title: ")
        desc = self.get_string_input("Enter task description: ")
        duration = self.get_string_input("Enter duration (minutes): ")
        
        try:
            duration = int(duration)
        except ValueError:
            return
        
        task = {
            "title": title,
            "description": desc,
            "duration": duration,
            "language": self.languages[self.current_language],
            "status": "Not Started"
        }
        
        self.tasks.append(task)
        self.save_to_csv()
        self.display_tasks()

    def start_timer(self):
        if not self.tasks:
            return
        
        if self.current_timer and self.current_timer.is_alive():
            return
        
        current_task = self.tasks[-1]
        duration = int(current_task["duration"])
        
        self.current_timer = TimerThread(duration, self.display_timer)
        self.current_timer.start()
        
        current_task["status"] = "In Progress"
        self.display_tasks()

    def pause_timer(self):
        if self.current_timer:
            self.current_timer.stop()

    def stop_timer(self):
        if self.current_timer:
            self.current_timer.stop()
            self.display_timer(0)

    def save_to_csv(self):
        today = datetime.now().date()
        year_folder = os.path.join(os.getcwd(), str(today.year))
        month_folder = os.path.join(year_folder, today.strftime("%B"))
        day_folder = os.path.join(month_folder, str(today.day))
        
        os.makedirs(day_folder, exist_ok=True)
        
        csv_filename = os.path.join(day_folder, f"{today.strftime('%Y-%m-%d')}_tasks.csv")
        
        csv_data = []
        for task in self.tasks:
            csv_data.append({
                "Tanggal": today,
                "Judul": task["title"],
                "Deskripsi": task["description"],
                "Durasi": task["duration"],
                "Bahasa": task["language"],
                "Status": task["status"]
            })
        
        df = pd.DataFrame(csv_data)
        df.to_csv(csv_filename, index=False, encoding="utf-8")

    def visualize_data(self, year: Optional[int] = None):
        if year is None:
            year = datetime.now().year

        try:
            year_folder = os.path.join(os.getcwd(), str(year))
            if not os.path.exists(year_folder):
                return

            all_tasks_data = []
            for month_dir in os.listdir(year_folder):
                month_path = os.path.join(year_folder, month_dir)
                if os.path.isdir(month_path):
                    for day_dir in os.listdir(month_path):
                        day_path = os.path.join(month_path, day_dir)
                        if os.path.isdir(day_path):
                            for file in os.listdir(day_path):
                                if file.endswith("_tasks.csv"):
                                    file_path = os.path.join(day_path, file)
                                    try:
                                        df = pd.read_csv(file_path)
                                        df["Tanggal"] = pd.to_datetime(df["Tanggal"])
                                        all_tasks_data.append(df)
                                    except Exception:
                                        continue

            if not all_tasks_data:
                return

            combined_df = pd.concat(all_tasks_data, ignore_index=True)
            
            plt.figure(figsize=(15, 6))
            
            # Language distribution
            plt.subplot(1, 2, 1)
            language_counts = combined_df["Bahasa"].value_counts()
            language_counts.plot(kind="pie", autopct="%1.1f%%")
            plt.title(f"Programming Language Distribution\n{year}")
            
            # Tasks per month
            plt.subplot(1, 2, 2)
            monthly_tasks = combined_df.groupby(combined_df["Tanggal"].dt.month_name()).size()
            monthly_tasks.plot(kind="bar")
            plt.title(f"Tasks per Month\n{year}")
            plt.xticks(rotation=45)
            
            plt.tight_layout()
            
            # Save visualization
            output_folder = os.path.join(year_folder, "Visualizations")
            os.makedirs(output_folder, exist_ok=True)
            output_path = os.path.join(output_folder, f"TaskVisualization_{year}.png")
            plt.savefig(output_path)
            plt.close()

        except Exception as e:
            self.screen.addstr(self.screen.getmaxyx()[0]-1, 0, f"Error: {str(e)}")
            self.screen.refresh()

    def run(self):
        while True:
            self.display_menu()
            self.display_tasks()
            
            key = self.screen.getch()
            
            if key == curses.KEY_UP and self.current_option > 0:
                self.current_option -= 1
            elif key == curses.KEY_DOWN and self.current_option < len(self.menu_options) - 1:
                self.current_option += 1
            elif key == ord('\n'):  # Enter key
                if self.menu_options[self.current_option] == "Exit":
                    break
                elif self.menu_options[self.current_option] == "Add Task":
                    self.add_task()
                elif self.menu_options[self.current_option] == "Start Timer":
                    self.start_timer()
                elif self.menu_options[self.current_option] == "Pause Timer":
                    self.pause_timer()
                elif self.menu_options[self.current_option] == "Stop Timer":
                    self.stop_timer()
                elif self.menu_options[self.current_option] == "Visualize Data":
                    self.visualize_data()
            elif key == ord('q'):
                break
            elif key == ord('l'):  # Cycle through programming languages
                self.current_language = (self.current_language + 1) % len(self.languages)


def main():
    curses.wrapper(lambda stdscr: PomodoroApp(stdscr).run())


if __name__ == "__main__":
    main()
