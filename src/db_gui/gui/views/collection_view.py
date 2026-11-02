"""Focused Database view"""

import customtkinter as ctk
from pymongo.errors import PyMongoError

class CollectionView(ctk.CTkFrame):
    """Show collections available to the authenticated user."""
    
    def __init__(
        self,
        master: ctk.CTk,
        database,
        back,
        collections,
        create_collection,
    ) -> None:
        super().__init__(master)
        self._database_name = database
        self._back = back
        self._collections = collections
        self._create_collection = create_collection
        self._build_view()
        
    def _build_view(self) -> None:
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(
            self,
            text=f"{self._database_name} collections",
            font=ctk.CTkFont(size=24, weight="bold"),
        ).grid(row=0, column=0, padx=30, pady=(30, 8), sticky="w")
        ctk.CTkLabel(
            self,
            text="Select a collection to continue.",
        ).grid(row=1, column=0, padx=30, pady=(0, 16), sticky="w")

        self._collections_list = ctk.CTkScrollableFrame(self, height=300)
        self._collections_list.grid(
            row=2, column=0, columnspan=2, padx=30, pady=10, sticky="nsew"
        )
        self._error_label = ctk.CTkLabel(self, text="", text_color="#d9534f")
        self._error_label.grid(
            row=4, column=0, columnspan=2, padx=30, sticky="w"
        )
        ctk.CTkButton(
            self, text="Add Collection", command=self._prompt_create_collections
        ).grid(row=3, column=0, padx=30, pady=20, sticky="w")
        ctk.CTkButton(
            self, text="Back", command=self._back, width=120
        ).grid(row=3, column=1, padx=30, pady=20, sticky="e")
        self._populate_collections(self._collections(self._database_name))
    
    def _populate_collections(self, collections: list[str]) -> None:
        for child in self._collections_list.winfo_children():
            child.destroy()
        for collection in collections:
            ctk.CTkButton(
                self._collections_list,
                text=collection,
                anchor="w",
                state = "disabled"
            ).pack(fill="x", pady=4)

        if not collections:
            ctk.CTkLabel(self._collections_list, text="No collections were found.").pack(
                pady=20
            )
    
    def _prompt_create_collections(self) -> None:
        collection_name = ctk.CTkInputDialog(
            text="Collection name:", title="Create collection"
        ).get_input()
        if collection_name is None:
            return

        try:
            collection = self._create_collection(
                self._database_name, collection_name
            )
        except ValueError as error:
            self._error_label.configure(text=str(error))
        except PyMongoError:
            self._error_label.configure(
                text="Could not create collection. Check its name and your permissions."
            )
        else:
            self._error_label.configure(text="")
            self._populate_collections(collection)