import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import os
import time
import threading
from datetime import datetime
import json
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys
import string
from ctypes import windll

class FileMonitorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("File Pulse")
        self.root.geometry("1000x700")
        self.root.configure(bg='#ece9d8')
        
        # Центрирование окна
        self.center_window()
        
        # Стиль для Windows 7
        self.setup_style()
        
        # Переменные
        self.monitoring = False
        self.observer = None
        self.watch_paths = self.get_all_drives()
        self.log_file = "file_monitor_log.json"
        self.current_drive = tk.StringVar(value="Все диски")
        
        # Загрузка истории
        self.file_history = self.load_history()
        
        self.setup_ui()
        
    def center_window(self):
        """Центрирует окно на экране"""
        self.root.update_idletasks()
        width = 1000
        height = 700
        x = (self.root.winfo_screenwidth() // 2) - (width // 2)
        y = (self.root.winfo_screenheight() // 2) - (height // 2)
        self.root.geometry('{}x{}+{}+{}'.format(width, height, x, y))
        
    def setup_style(self):
        style = ttk.Style()
        style.theme_use('winnative')
        
    def get_all_drives(self):
        """Получает список всех дисков в системе без использования psutil"""
        drives = []
        # Получаем битовую маску дисков
        bitmask = windll.kernel32.GetLogicalDrives()
        for letter in string.ascii_uppercase:
            if bitmask & 1:
                drive_path = letter + ':\\'
                if os.path.exists(drive_path):
                    drives.append(drive_path)
            bitmask >>= 1
        return drives
        
    def setup_ui(self):
        # Главный фрейм
        main_frame = tk.Frame(self.root, bg='#ece9d8', relief='sunken', bd=1)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=8, pady=8)
        
        # Заголовок
        header_frame = tk.Frame(main_frame, bg='#ece9d8')
        header_frame.pack(fill=tk.X, pady=(0, 15))
        
        title_label = tk.Label(header_frame, 
                              text="Монитор файловой системы Windows",
                              font=('Segoe UI', 16, 'bold'), 
                              bg='#ece9d8', fg='#003399')
        title_label.pack(side=tk.LEFT)
        
        # Панель информации о системе
        info_frame = ttk.LabelFrame(main_frame, text="Информация о системе")
        info_frame.pack(fill=tk.X, pady=(0, 10))
        
        info_text = tk.Text(info_frame, height=3, font=('Segoe UI', 9),
                           bg='#f5f5f5', relief='flat', wrap=tk.WORD)
        info_text.pack(fill=tk.X, padx=5, pady=5)
        
        drives_info = ", ".join(self.watch_paths)
        info_text.insert(tk.END, 
                        f"Мониторинг всех дисков системы:\n"
                        f"Доступные диски: {drives_info}\n"
                        f"Всего дисков: {len(self.watch_paths)}")
        info_text.config(state=tk.DISABLED)
        
        # Панель управления
        control_frame = ttk.LabelFrame(main_frame, text="Управление мониторингом")
        control_frame.pack(fill=tk.X, pady=(0, 10))
        
        # Выбор диска
        drive_frame = tk.Frame(control_frame, bg='#ece9d8')
        drive_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(drive_frame, text="Мониторинг:", 
                bg='#ece9d8', font=('Segoe UI', 9)).pack(side=tk.LEFT)
        
        drive_combo = ttk.Combobox(drive_frame, 
                                  textvariable=self.current_drive,
                                  values=["Все диски"] + self.watch_paths,
                                  state="readonly", width=30)
        drive_combo.pack(side=tk.LEFT, padx=5)
        drive_combo.bind('<<ComboboxSelected>>', self.on_drive_change)
        
        # Кнопки управления
        button_frame = tk.Frame(control_frame, bg='#ece9d8')
        button_frame.pack(fill=tk.X, pady=8)
        
        self.start_btn = tk.Button(button_frame, text="Начать", 
                                  command=self.start_monitoring,
                                  bg='#d4d0c8', relief='raised', bd=2,
                                  font=('Segoe UI', 10), width=15)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        self.stop_btn = tk.Button(button_frame, text="Остановить", 
                                 command=self.stop_monitoring, 
                                 state=tk.DISABLED,
                                 bg='#d4d0c8', relief='raised', bd=2,
                                 font=('Segoe UI', 10), width=15)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        clear_btn = tk.Button(button_frame, text="Очистить историю", 
                             command=self.clear_history,
                             bg='#d4d0c8', relief='raised', bd=2,
                             font=('Segoe UI', 10), width=15)
        clear_btn.pack(side=tk.LEFT, padx=(0, 5))
        
        export_btn = tk.Button(button_frame, text="Экспорт данных", 
                              command=self.export_data,
                              bg='#d4d0c8', relief='raised', bd=2,
                              font=('Segoe UI', 10), width=15)
        export_btn.pack(side=tk.LEFT)
        
        # Статус бар
        status_frame = tk.Frame(control_frame, bg='#ece9d8', relief='sunken', bd=1)
        status_frame.pack(fill=tk.X, pady=5)
        
        self.status_var = tk.StringVar(value="Мониторинг остановлен")
        status_label = tk.Label(status_frame, textvariable=self.status_var, 
                               bg='#f0f0f0', fg='red', 
                               font=('Segoe UI', 10, 'bold'),
                               relief='sunken', bd=1)
        status_label.pack(fill=tk.X, padx=2, pady=2)
        
        # Статистика
        stats_frame = tk.Frame(control_frame, bg='#ece9d8')
        stats_frame.pack(fill=tk.X, pady=5)
        
        self.stats_var = tk.StringVar(value="Файлов в истории: 0")
        stats_label = tk.Label(stats_frame, textvariable=self.stats_var,
                              bg='#ece9d8', font=('Segoe UI', 9))
        stats_label.pack(side=tk.LEFT)
        
        # Таблица с файлами
        list_frame = ttk.LabelFrame(main_frame, text="История создания файлов")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        # Создаем Treeview с колонками
        columns = ('time', 'filename', 'path', 'size', 'drive')
        self.tree = ttk.Treeview(list_frame, columns=columns, show='headings')
        
        # Настраиваем колонки
        self.tree.heading('time', text='Время создания')
        self.tree.heading('filename', text='Имя файла')
        self.tree.heading('path', text='Путь')
        self.tree.heading('size', text='Размер')
        self.tree.heading('drive', text='Диск')
        
        self.tree.column('time', width=150, anchor='center')
        self.tree.column('filename', width=200)
        self.tree.column('path', width=350)
        self.tree.column('size', width=100, anchor='center')
        self.tree.column('drive', width=80, anchor='center')
        
        # Scrollbar для таблицы
        v_scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tree.yview)
        h_scrollbar = ttk.Scrollbar(list_frame, orient=tk.HORIZONTAL, command=self.tree.xview)
        self.tree.configure(yscrollcommand=v_scrollbar.set, xscrollcommand=h_scrollbar.set)
        
        # Размещение элементов
        self.tree.grid(row=0, column=0, sticky='nsew')
        v_scrollbar.grid(row=0, column=1, sticky='ns')
        h_scrollbar.grid(row=1, column=0, sticky='ew')
        
        list_frame.grid_rowconfigure(0, weight=1)
        list_frame.grid_columnconfigure(0, weight=1)
        
        # Контекстное меню
        self.setup_context_menu()
        
        # Загружаем историю в таблицу
        self.refresh_file_list()
        
    def setup_context_menu(self):
        self.context_menu = tk.Menu(self.root, tearoff=0, font=('Segoe UI', 9))
        self.context_menu.add_command(label="Открыть файл", command=self.open_selected_file)
        self.context_menu.add_command(label="Открыть папку", command=self.open_selected_folder)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Копировать путь", command=self.copy_path)
        self.context_menu.add_separator()
        self.context_menu.add_command(label="Удалить из истории", command=self.remove_from_history)
        
        self.tree.bind("<Button-3>", self.show_context_menu)
        
    def show_context_menu(self, event):
        item = self.tree.identify_row(event.y)
        if item:
            self.tree.selection_set(item)
            self.context_menu.post(event.x_root, event.y_root)
            
    def on_drive_change(self, event=None):
        """Обработчик изменения выбранного диска"""
        self.refresh_file_list()
            
    def open_selected_file(self):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            path = os.path.join(item['values'][2], item['values'][1])
            try:
                os.startfile(path)
            except:
                messagebox.showerror("Ошибка", "Не удалось открыть файл")
                
    def open_selected_folder(self):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            path = item['values'][2]
            try:
                os.startfile(path)
            except:
                messagebox.showerror("Ошибка", "Не удалось открыть папку")
                
    def copy_path(self):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            path = os.path.join(item['values'][2], item['values'][1])
            self.root.clipboard_clear()
            self.root.clipboard_append(path)
            messagebox.showinfo("Успех", "Путь скопирован в буфер обмена")
            
    def remove_from_history(self):
        selection = self.tree.selection()
        if selection:
            item = self.tree.item(selection[0])
            filename = item['values'][1]
            path = item['values'][2]
            
            # Удаляем из истории
            self.file_history = [f for f in self.file_history 
                               if not (f['filename'] == filename and f['path'] == path)]
            self.save_history()
            self.refresh_file_list()
            
    def load_history(self):
        try:
            if os.path.exists(self.log_file):
                with open(self.log_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Ошибка загрузки истории: {e}")
        return []
        
    def save_history(self):
        try:
            with open(self.log_file, 'w', encoding='utf-8') as f:
                json.dump(self.file_history, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Ошибка сохранения: {e}")
            
    def refresh_file_list(self):
        # Очищаем таблицу
        for item in self.tree.get_children():
            self.tree.delete(item)
            
        # Фильтрация по выбранному диску
        filtered_history = self.file_history
        if self.current_drive.get() != "Все диски":
            drive = self.current_drive.get()
            filtered_history = [f for f in self.file_history if f['path'].startswith(drive)]
            
        # Сортируем по времени (новые сверху)
        sorted_history = sorted(filtered_history, 
                               key=lambda x: x['timestamp'], reverse=True)
        
        # Заполняем таблицу
        for item in sorted_history:
            time_str = datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
            size_str = self.format_size(item['size'])
            drive_letter = item['path'][:2] if len(item['path']) >= 2 else "?"
            
            self.tree.insert('', 0, values=(
                time_str, item['filename'], item['path'], size_str, drive_letter
            ))
            
        # Обновляем статистику
        self.stats_var.set(f"Файлов в истории: {len(self.file_history)} | "
                          f"Отображено: {len(sorted_history)}")
            
    def format_size(self, size):
        for unit in ['Б', 'КБ', 'МБ', 'ГБ']:
            if size < 1024.0:
                return f"{size:.1f} {unit}"
            size /= 1024.0
        return f"{size:.1f} ТБ"
        
    def start_monitoring(self):
        if not self.watch_paths:
            messagebox.showerror("Ошибка", "Не найдено доступных дисков для мониторинга!")
            return
            
        self.monitoring = True
        self.start_btn.config(state=tk.DISABLED, bg='#c0c0c0')
        self.stop_btn.config(state=tk.NORMAL, bg='#d4d0c8')
        self.status_var.set("Мониторинг активен - отслеживаются все диски")
        
        # Запускаем мониторинг в отдельном потоке
        self.monitor_thread = threading.Thread(target=self.run_monitoring, daemon=True)
        self.monitor_thread.start()
        
    def stop_monitoring(self):
        self.monitoring = False
        self.start_btn.config(state=tk.NORMAL, bg='#d4d0c8')
        self.stop_btn.config(state=tk.DISABLED, bg='#c0c0c0')
        self.status_var.set("Мониторинг остановлен")
        
        if hasattr(self, 'observers'):
            for observer in self.observers:
                if observer:
                    observer.stop()
                    observer.join()
            
    def run_monitoring(self):
        class FileHandler(FileSystemEventHandler):
            def __init__(self, callback):
                self.callback = callback
                
            def on_created(self, event):
                if not event.is_directory:
                    self.callback(event.src_path)
                    
            def on_modified(self, event):
                if not event.is_directory:
                    self.callback(event.src_path)
        
        # Создаем наблюдателей для всех дисков
        observers = []
        for drive in self.watch_paths:
            try:
                event_handler = FileHandler(self.on_file_created)
                observer = Observer()
                observer.schedule(event_handler, drive, recursive=True)
                observers.append(observer)
                observer.start()
                print(f"Мониторинг запущен для диска: {drive}")
            except Exception as e:
                print(f"Ошибка мониторинга диска {drive}: {e}")
        
        self.observers = observers
        
        try:
            while self.monitoring:
                time.sleep(0.5)
        except:
            pass
            
    def on_file_created(self, file_path):
        try:
            # Даем файлу время на создание
            time.sleep(0.1)
            
            if os.path.exists(file_path):
                # Пропускаем системные и временные файлы
                if any(x in file_path.lower() for x in ['.tmp', 'temp\\', '\\tmp\\', '$']):
                    return
                    
                stat = os.stat(file_path)
                
                # Игнорируем очень маленькие файлы (возможно временные)
                if stat.st_size == 0:
                    return
                    
                file_info = {
                    'timestamp': stat.st_ctime,
                    'filename': os.path.basename(file_path),
                    'path': os.path.dirname(file_path),
                    'size': stat.st_size
                }
                
                # Проверяем, нет ли уже такого файла в истории
                if not any(f['path'] == file_info['path'] and 
                          f['filename'] == file_info['filename'] and
                          abs(f['timestamp'] - file_info['timestamp']) < 1 
                          for f in self.file_history):
                    self.file_history.append(file_info)
                    self.save_history()
                    
                    # Обновляем UI в главном потоке
                    self.root.after(0, self.refresh_file_list)
                    
        except Exception as e:
            print(f"Ошибка обработки файла {file_path}: {e}")
            
    def clear_history(self):
        if messagebox.askyesno("Подтверждение", 
                              "Очистить всю историю файлов?\nЭто действие нельзя отменить."):
            self.file_history.clear()
            self.save_history()
            self.refresh_file_list()
            messagebox.showinfo("Успех", "История очищена")
            
    def export_data(self):
        """Экспорт данных в CSV файл"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Экспорт данных мониторинга"
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("Время;Имя файла;Путь;Размер;Диск\n")
                    for item in self.file_history:
                        time_str = datetime.fromtimestamp(item['timestamp']).strftime('%Y-%m-%d %H:%M:%S')
                        drive_letter = item['path'][:2] if len(item['path']) >= 2 else "?"
                        f.write(f"{time_str};{item['filename']};{item['path']};{item['size']};{drive_letter}\n")
                messagebox.showinfo("Успех", f"Данные экспортированы в {filename}")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось экспортировать данные: {e}")
            
    def on_closing(self):
        self.stop_monitoring()
        self.save_history()
        self.root.destroy()

def main():
    # Проверяем наличие watchdog
    try:
        import watchdog
    except ImportError:
        print("Установите библиотеку watchdog: pip install watchdog")
        messagebox.showerror("Ошибка", "Установите библиотеку watchdog:\npip install watchdog")
        return
        
    root = tk.Tk()
    app = FileMonitorApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
        
    root.mainloop()

if __name__ == "__main__":
    main()
