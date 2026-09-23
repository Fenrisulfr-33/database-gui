"""Database home view."""

import customtkinter as ctk


class DatabaseView(ctk.CTkFrame):
    """Show databases available to the authenticated user."""

    def __init__(self, master: ctk.CTk, databases: list[str], logout) -> None:
        super().__init__(master)
        self._build_view(databases, logout)

    def _build_view(self, databases: list[str], logout) -> None:
        self.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(
            self,
            text="Database home",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=30, pady=(30, 8), sticky="w")
        ctk.CTkLabel(
            self,
            text="Select a database to continue.",
        ).grid(row=1, column=0, padx=30, pady=(0, 16), sticky="w")

        database_list = ctk.CTkScrollableFrame(self, height=300)
        database_list.grid(row=2, column=0, padx=30, pady=10, sticky="nsew")
        for database in databases:
            ctk.CTkButton(
                database_list, text=database, anchor="w", state="disabled"
            ).pack(fill="x", pady=4)

        if not databases:
            ctk.CTkLabel(database_list, text="No databases were found.").pack(
                pady=20
            )
        ctk.CTkButton(self, text="Disconnect", command=logout, width=120).grid(
            row=3, column=0, padx=30, pady=20, sticky="w"
        )