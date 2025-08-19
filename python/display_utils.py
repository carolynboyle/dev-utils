"""
display_utils.py
----------------
Helpers for rendering tabular data in a CLI.
"""

from cli_utils import clear_screen

def display_records(records, headers=None, title="Records", show_count=True, page_size=10, enable_paging=True) -> int:
    """Display records in pages. Returns total records shown."""
    if not records:
        print(f'No {title.lower()} found')
        return 0

    total_records = len(records)
    if not enable_paging or total_records <= page_size:
        return _display_records_page(records, headers, title, show_count, total_records)

    total_pages = (total_records + page_size - 1) // page_size
    current_page = 1
    while True:
        clear_screen()
        start = (current_page - 1) * page_size
        end = min(start + page_size, total_records)
        current_page_records = records[start:end]

        print(f"\n{title} (Page {current_page} of {total_pages}):\n")
        _print_table(current_page_records, headers)

        print(f"\nShowing records {start+1}-{end} of {total_records}")
        print("Options: [P]rev [N]ext [F]irst [L]ast [Q]uit")
        choice = input("Choice: ").strip().upper()
        if choice == 'Q': break
        elif choice == 'N' and current_page < total_pages: current_page += 1
        elif choice == 'P' and current_page > 1: current_page -= 1
        elif choice == 'F': current_page = 1
        elif choice == 'L': current_page = total_pages
    return total_records

def _display_records_page(records, headers, title, show_count, total_records=None) -> int:
    """Helper for single-page display."""
    if total_records is None:
        total_records = len(records)
    print(f"\n{title}:\n")
    _print_table(records, headers)
    if show_count:
        print(f"\nTotal records: {total_records}")
    return len(records)

def _print_table(records, headers):
    if headers:
        header_row = " | ".join(str(h).ljust(15) for h in headers)
        print(header_row)
        print("-" * len(header_row))
    for idx, record in enumerate(records, start=1):
        try:
            if isinstance(record, (tuple, list)):
                row = f"{str(idx).ljust(4)} | " + " | ".join(str(f).ljust(15) for f in record)
            else:
                row = f"{str(idx).ljust(4)} | {str(record).ljust(15)}"
            print(row)
        except Exception as e:
            print(f"Error displaying record {idx}: {e}")
