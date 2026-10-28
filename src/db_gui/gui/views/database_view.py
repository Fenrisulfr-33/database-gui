"""Database home view."""

import customtkinter as ctk


class DatabaseView(ctk.CTkFrame):
    """Show databases available to the authenticated user."""

    def __init__(
        self, master: ctk.CTk, databases: list[str], rename_database, logout
    ) -> None:
        super().__init__(master)
        self._build_view(databases, rename_database, logout)

    def _build_view(self, databases: list[str], rename_database, logout) -> None:
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
            self._add_database_row(database_list, database, rename_database)

        if not databases:
            ctk.CTkLabel(database_list, text="No databases were found.").pack(
                pady=20
            )
        ctk.CTkButton(self, text="Disconnect", command=logout, width=120).grid(
            row=3, column=0, padx=30, pady=20, sticky="w"
        )

    @staticmethod
    def _add_database_row(database_list, database: str, rename_database) -> None:
        row = ctk.CTkFrame(database_list, fg_color="transparent")
        row.pack(fill="x", pady=4)
        ctk.CTkLabel(row, text=database, anchor="w").pack(
            side="left", fill="x", expand=True, padx=8
        )
        ctk.CTkButton(
            row,
            text="Rename",
            width=90,
            command=lambda: rename_database(database),
        ).pack(side="right")