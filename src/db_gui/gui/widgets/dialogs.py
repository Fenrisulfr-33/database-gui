"""Pop-up dialogs."""

from collections.abc import Callable

import customtkinter as ctk

# starting text so the user types between the braces
JSON_TEMPLATE = "{\n  \n}"


class JsonDocumentDialog(ctk.CTkToplevel):
    """Pop-up with a text box for typing a JSON document."""

    def __init__(
        self,
        master: ctk.CTkBaseClass,
        on_submit: Callable[[str], str | None],
    ) -> None:
        super().__init__(master)
        self._on_submit = on_submit
        self.title("Add document")
        self.geometry("520x420")
        self.transient(master)
        self._build_dialog()
        # grab_set fails if the window is not shown yet, so wait a bit
        self.after(100, self._make_modal)

    def _build_dialog(self) -> None:
        """Put the widgets in the window."""
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)
        ctk.CTkLabel(self, text="Document (JSON):").grid(
            row=0, column=0, columnspan=2, padx=20, pady=(20, 6), sticky="w"
        )
        self._textbox = ctk.CTkTextbox(
            self, font=ctk.CTkFont(family="Courier", size=13)
        )
        self._textbox.grid(
            row=1, column=0, columnspan=2, padx=20, pady=6, sticky="nsew"
        )
        self._textbox.insert("1.0", JSON_TEMPLATE)
        self._error_label = ctk.CTkLabel(
            self, text="", text_color="#d9534f", wraplength=470, justify="left"
        )
        self._error_label.grid(
            row=2, column=0, columnspan=2, padx=20, sticky="w"
        )
        self._build_buttons()

    def _build_buttons(self) -> None:
        """Cancel and Add document buttons."""
        ctk.CTkButton(
            self, text="Cancel", width=120, command=self.destroy
        ).grid(row=3, column=0, padx=20, pady=20, sticky="w")
        ctk.CTkButton(
            self, text="Add document", command=self._submit
        ).grid(row=3, column=1, padx=20, pady=20, sticky="e")

    def _make_modal(self) -> None:
        """Stop clicks on the window behind until this closes."""
        self.grab_set()
        self._textbox.focus()

    def _submit(self) -> None:
        """Close on success, show the error if it failed."""
        error = self._on_submit(self._textbox.get("1.0", "end"))
        if error:
            self._error_label.configure(text=error)
        else:
            self.destroy()
