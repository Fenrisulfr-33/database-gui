"""Cluster login view."""

import customtkinter as ctk


class ConnectionView(ctk.CTkFrame):
    """Collect cluster credentials and report the login attempt."""

    def __init__(self, master: ctk.CTk, submit_login) -> None:
        super().__init__(master)
        self._submit_login = submit_login
        self._build_form()

    def _build_form(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        form = ctk.CTkFrame(self, fg_color="transparent")
        form.grid(row=0, column=0, padx=40, pady=50)

        ctk.CTkLabel(
            form,
            text="Connect to a cluster",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, pady=(0, 8))
        ctk.CTkLabel(
            form,
            text="Sign in to view the databases you can access.",
        ).grid(row=1, column=0, pady=(0, 24))

        self._uri_entry = self._add_entry(form, "Cluster URI", 2)
        self._username_entry = self._add_entry(form, "Username", 3)
        self._password_entry = self._add_entry(form, "Password", 4, True)
        self._error_label = ctk.CTkLabel(form, text="", text_color="#d9534f")
        self._error_label.grid(row=5, column=0, pady=(10, 4))
        ctk.CTkButton(form, text="Connect", command=self._submit).grid(
            row=6, column=0, pady=(8, 0), sticky="ew"
        )

    def _add_entry(self, parent, placeholder: str, row: int, secret=False):
        entry = ctk.CTkEntry(parent, width=340, placeholder_text=placeholder)
        if secret:
            entry.configure(show="*")
        entry.grid(row=row, column=0, pady=6)
        return entry

    def _submit(self) -> None:
        self._error_label.configure(text="")
        password = self._password_entry.get()
        self._password_entry.delete(0, "end")
        self._submit_login(
            self._uri_entry.get(), self._username_entry.get(), password
        )

    def show_error(self, message: str) -> None:
        """Display a safe, readable login error."""
        self._error_label.configure(text=message)