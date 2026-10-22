"""
Book Inventory Manager - Capstone App
OOP data model + JSON file storage + multi-view Flet UI.
"""
import json
from pathlib import Path

import flet as ft

DATA_FILE = Path(__file__).with_name("books.json")
LOW_STOCK_LIMIT = 3


# =====================================================================
# 1. DATA MODEL (OOP)
# =====================================================================
class Book:
    def __init__(self, book_id, title, author, rating, stock):
        self.id = book_id
        self.title = title
        self.author = author
        self.rating = rating
        self.stock = stock

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "author": self.author,
            "rating": self.rating,
            "stock": self.stock,
        }

    @staticmethod
    def from_dict(data):
        return Book(
            int(data["id"]),
            data["title"],
            data["author"],
            int(data["rating"]),
            int(data["stock"]),
        )


def parse_book_input(title, author, rating, stock):
    """Validate raw form text. Raises ValueError with a friendly message."""
    title = (title or "").strip()
    author = (author or "").strip()
    if not title:
        raise ValueError("Please enter a title.")
    if not author:
        raise ValueError("Please enter an author.")
    try:
        rating = int(str(rating).strip())
    except ValueError:
        raise ValueError("Rating must be a whole number from 1 to 10.")
    if not 1 <= rating <= 10:
        raise ValueError("Rating must be between 1 and 10.")
    try:
        stock = int(str(stock).strip())
    except ValueError:
        raise ValueError("Stock must be a whole number (0 or more).")
    if stock < 0:
        raise ValueError("Stock cannot be negative.")
    return title, author, rating, stock


class Inventory:
    """Holds all books and saves/loads them from a JSON file."""

    def __init__(self, filename=DATA_FILE):
        self.filename = Path(filename)
        self.books = []
        self.load()

    # ---- storage ----
    def load(self):
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                self.books = [Book.from_dict(d) for d in json.load(f)]
        except FileNotFoundError:
            self.books = [
                Book(1, "Atomic Habits", "James Clear", 9, 12),
                Book(2, "Clean Code", "Robert Martin", 8, 2),
                Book(3, "1984", "George Orwell", 10, 5),
            ]
            self.save()
        except (json.JSONDecodeError, KeyError, TypeError, ValueError):
            print("The data file was damaged, starting with an empty inventory.")
            self.books = []

    def save(self):
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump([b.to_dict() for b in self.books], f, indent=2)
        except OSError as error:
            print("Could not save the data file:", error)

    # ---- operations ----
    def next_id(self):
        return max((b.id for b in self.books), default=0) + 1

    def get(self, book_id):
        for book in self.books:
            if str(book.id) == str(book_id):
                return book
        return None

    def add(self, title, author, rating, stock):
        book = Book(self.next_id(), title, author, rating, stock)
        self.books.append(book)
        self.save()
        return book

    def update(self, book_id, title, author, rating, stock):
        book = self.get(book_id)
        if book is None:
            return None
        book.title, book.author = title, author
        book.rating, book.stock = rating, stock
        self.save()
        return book

    def delete(self, book_id):
        book = self.get(book_id)
        if book is None:
            return False
        self.books.remove(book)
        self.save()
        return True

    def search(self, text):
        text = (text or "").strip().lower()
        if not text:
            return list(self.books)
        return [
            b for b in self.books
            if text in b.title.lower() or text in b.author.lower()
        ]

    # ---- statistics ----
    def total_titles(self):
        return len(self.books)

    def total_stock(self):
        return sum(b.stock for b in self.books)

    def average_rating(self):
        if not self.books:
            return 0.0
        return sum(b.rating for b in self.books) / len(self.books)

    def low_stock(self):
        return [b for b in self.books if b.stock <= LOW_STOCK_LIMIT]


# =====================================================================
# 2. USER INTERFACE (Flet, multi-view)
# =====================================================================
def main(page: ft.Page):
    page.title = "Book Inventory Manager"
    page.theme_mode = ft.ThemeMode.LIGHT
    page.theme = ft.Theme(color_scheme_seed=ft.Colors.INDIGO)

    inventory = Inventory()
    search_text = ""  # shared so the search survives view changes

    def notify(message):
        page.show_dialog(ft.SnackBar(ft.Text(message)))

    # ---- navigation handlers ----
    async def go_home(e):
        await page.push_route("/")

    async def go_add(e):
        await page.push_route("/add")

    async def go_stats(e):
        await page.push_route("/stats")

    def make_edit_handler(book_id):
        async def handler(e):
            await page.push_route(f"/edit/{book_id}")
        return handler

    def make_delete_handler(book):
        def ask(e):
            def cancel(ev):
                page.pop_dialog()

            def confirm(ev):
                inventory.delete(book.id)
                page.pop_dialog()
                route_change()
                notify(f"Deleted '{book.title}'.")

            page.show_dialog(
                ft.AlertDialog(
                    title=ft.Text("Delete book?"),
                    content=ft.Text(f"Remove '{book.title}' from the inventory?"),
                    actions=[
                        ft.TextButton("Cancel", on_click=cancel),
                        ft.TextButton("Delete", on_click=confirm),
                    ],
                )
            )
        return ask

    # ---- VIEW 1: home (list + search) ----
    def build_book_card(book):
        low = book.stock <= LOW_STOCK_LIMIT
        details = f"by {book.author}  |  Rating {book.rating}/10  |  Stock {book.stock}"
        if low:
            details += "  (LOW STOCK)"
        return ft.Card(
            content=ft.Container(
                padding=12,
                content=ft.Row(
                    [
                        ft.Icon(ft.Icons.MENU_BOOK),
                        ft.Column(
                            [
                                ft.Text(book.title, weight=ft.FontWeight.BOLD, size=16),
                                ft.Text(
                                    details,
                                    color=ft.Colors.RED if low else None,
                                ),
                            ],
                            expand=True,
                            spacing=2,
                        ),
                        ft.IconButton(
                            icon=ft.Icons.EDIT,
                            tooltip="Edit",
                            on_click=make_edit_handler(book.id),
                        ),
                        ft.IconButton(
                            icon=ft.Icons.DELETE,
                            tooltip="Delete",
                            on_click=make_delete_handler(book),
                        ),
                    ],
                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                ),
            )
        )

    def build_home_view():
        list_column = ft.Column(spacing=8, scroll=ft.ScrollMode.AUTO, expand=True)

        def refresh_list():
            list_column.controls.clear()
            results = inventory.search(search_text)
            if not results:
                list_column.controls.append(ft.Text("No books found.", italic=True))
            for book in results:
                list_column.controls.append(build_book_card(book))

        def search_changed(e):
            nonlocal search_text
            search_text = e.control.value or ""
            refresh_list()
            page.update()

        refresh_list()

        return ft.View(
            route="/",
            padding=20,
            appbar=ft.AppBar(
                title=ft.Text("Book Inventory"),
                actions=[
                    ft.IconButton(
                        icon=ft.Icons.BAR_CHART,
                        tooltip="Statistics",
                        on_click=go_stats,
                    )
                ],
            ),
            controls=[
                ft.TextField(
                    label="Search by title or author",
                    value=search_text,
                    prefix_icon=ft.Icons.SEARCH,
                    on_change=search_changed,
                ),
                ft.Button("Add book", icon=ft.Icons.ADD, on_click=go_add),
                list_column,
            ],
        )

    # ---- VIEW 2: add / edit form ----
    def build_form_view(book=None):
        editing = book is not None

        title_field = ft.TextField(label="Title", value=book.title if editing else "")
        author_field = ft.TextField(label="Author", value=book.author if editing else "")
        rating_field = ft.TextField(
            label="Rating (1-10)",
            value=str(book.rating) if editing else "",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        stock_field = ft.TextField(
            label="Stock (copies)",
            value=str(book.stock) if editing else "",
            keyboard_type=ft.KeyboardType.NUMBER,
        )
        error_text = ft.Text("", color=ft.Colors.RED)

        async def save_clicked(e):
            try:
                title, author, rating, stock = parse_book_input(
                    title_field.value,
                    author_field.value,
                    rating_field.value,
                    stock_field.value,
                )
            except ValueError as error:
                error_text.value = str(error)
                page.update()
                return

            if editing:
                inventory.update(book.id, title, author, rating, stock)
                notify(f"Updated '{title}'.")
            else:
                inventory.add(title, author, rating, stock)
                notify(f"Added '{title}'.")
            await page.push_route("/")

        return ft.View(
            route="/edit" if editing else "/add",
            padding=20,
            appbar=ft.AppBar(title=ft.Text("Edit book" if editing else "Add book")),
            controls=[
                title_field,
                author_field,
                rating_field,
                stock_field,
                error_text,
                ft.Row(
                    [
                        ft.Button("Save", icon=ft.Icons.SAVE, on_click=save_clicked),
                        ft.OutlinedButton("Cancel", on_click=go_home),
                    ]
                ),
            ],
        )

    # ---- VIEW 3: statistics ----
    def build_stats_view():
        low_books = inventory.low_stock()
        if low_books:
            low_lines = [
                ft.Text(f"- {b.title} ({b.stock} left)", color=ft.Colors.RED)
                for b in low_books
            ]
        else:
            low_lines = [ft.Text("No books are running low.")]

        return ft.View(
            route="/stats",
            padding=20,
            appbar=ft.AppBar(title=ft.Text("Statistics")),
            controls=[
                ft.Text(f"Titles in inventory: {inventory.total_titles()}", size=18),
                ft.Text(f"Total copies in stock: {inventory.total_stock()}", size=18),
                ft.Text(f"Average rating: {inventory.average_rating():.1f} / 10", size=18),
                ft.Text(f"Low stock (<= {LOW_STOCK_LIMIT} copies):", size=18, weight=ft.FontWeight.BOLD),
                *low_lines,
                ft.Button("Back", icon=ft.Icons.ARROW_BACK, on_click=go_home),
            ],
        )

    # ---- routing ----
    def route_change(e=None):
        page.views.clear()
        page.views.append(build_home_view())

        route = page.route
        if route == "/add":
            page.views.append(build_form_view())
        elif route.startswith("/edit/"):
            book = inventory.get(route.split("/")[-1])
            if book is not None:
                page.views.append(build_form_view(book))
        elif route == "/stats":
            page.views.append(build_stats_view())
        page.update()

    async def view_pop(e=None):
        await page.push_route("/")

    page.on_route_change = route_change
    page.on_view_pop = view_pop
    route_change()


ft.run(main)