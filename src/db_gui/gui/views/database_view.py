"""Database home view."""

import customtkinter as ctk
from pymongo.errors import PyMongoError


class DatabaseView(ctk.CTkFrame):
    """Show databases available to the authenticated user."""

    def __init__(
        self,
        master: ctk.CTk,
        databases: list[str],
        create_database,
        logout,
        collections,
    ) -> None:
        super().__init__(master)
        self._create_database_callback = create_database
        self._logout_callback = logout
        self._collections_callback = collections
        self._build_view(databases)

    def _build_view(self, databases: list[str]) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self,
            text="Database home",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=30, pady=(30, 8), sticky="w")
        ctk.CTkLabel(
            self,
            text="Select a database to continue.",
        ).grid(row=1, column=0, padx=30, pady=(0, 16), sticky="w")

        self._database_list = ctk.CTkScrollableFrame(self, height=300)
        self._database_list.grid(
            row=2, column=0, columnspan=2, padx=30, pady=10, sticky="nsew"
        )
        self._error_label = ctk.CTkLabel(self, text="", text_color="#d9534f")
        self._error_label.grid(
            row=4, column=0, columnspan=2, padx=30, sticky="w"
        )
        ctk.CTkButton(
            self, text="Add database", command=self._prompt_create_database
        ).grid(row=3, column=0, padx=30, pady=20, sticky="w")
        ctk.CTkButton(
            self, text="Disconnect", command=self._logout_callback, width=120
        ).grid(row=3, column=1, padx=30, pady=20, sticky="e")
        self._populate_databases(databases)

    def _populate_databases(self, databases: list[str]) -> None:
        for child in self._database_list.winfo_children():
            child.destroy()
        for database in databases:
            ctk.CTkButton(
                self._database_list,
                text=database,
                anchor="w",
                command= lambda name=database: self._collections_callback(name),
            ).pack(fill="x", pady=4)

        if not databases:
            ctk.CTkLabel(self._database_list, text="No databases were found.").pack(
                pady=20
            )

    def _prompt_create_database(self) -> None:
        database_name = ctk.CTkInputDialog(
            text="Database name:", title="Create database"
        ).get_input()
        if database_name is None:
            return

        collection_name = ctk.CTkInputDialog(
            text="Initial collection name:", title="Create database"
        ).get_input()
        if collection_name is None:
            return

        try:
            databases = self._create_database_callback(
                database_name, collection_name
            )
        except ValueError as error:
            self._error_label.configure(text=str(error))
        except PyMongoError:
            self._error_label.configure(
                text="Could not create database. Check its name and your permissions."
            )
        else:
            self._error_label.configure(text="")
            self._populate_databases(databases)
