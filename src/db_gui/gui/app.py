"""Root application window."""

import customtkinter as ctk


class App(ctk.CTk):
    """The main window. Views get swapped into this later as the app grows."""

    def __init__(self) -> None:
        super().__init__()

        ctk.set_appearance_mode("System")
        ctk.set_default_color_theme("blue")

        self.title("Database GUI Manager")
        self.geometry("900x600")
        self.minsize(600, 400)

        self._build_layout()

    def _build_layout(self) -> None:
        # Placeholder content — replace with connection_view / sidebar once
        # db/connection.py exists.
        label = ctk.CTkLabel(
            self,
            text="Database GUI Manager",
            font=ctk.CTkFont(size=20, weight="bold"),
        )
        label.pack(expand=True)


if __name__ == "__main__":
    # Lets you run this file directly (python src/db_gui/gui/app.py)
    # for quick UI iteration without going through main.py.
    App().mainloop()
