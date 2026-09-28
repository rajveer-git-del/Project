import csv
import logging
import os
import random
import time

# ---------- Configuration (change here, nowhere else) ----------
RESULTS_FILE = "typing_results.csv"
LOG_FILE = "typing_tester.log"
CSV_HEADERS = ["date", "mode", "wpm", "accuracy", "errors", "seconds"]
TIMED_OPTIONS = {"1": 15, "2": 30, "3": 60}   # menu choice -> seconds
MIN_WORDS = 3                                 # shortest sentence allowed
MAX_WORDS = 25                                # longest sentence allowed

# Fallback list, used only if wonderwords is not installed
WORDS = [
    "time", "code", "python", "simple", "practice", "keyboard", "quick",
    "screen", "logic", "function", "variable", "loop", "system", "typing",
    "speed", "learn", "build", "test", "error", "data", "file", "input",
    "output", "small", "clear", "focus", "steady", "improve", "daily",
    "program", "result", "accuracy", "player", "random", "word", "sentence",
    "fast", "smooth", "careful", "review", "skill", "brain", "hands",
    "rhythm", "pattern", "memory", "design", "module", "debug", "count",
]

logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
)


try:
    from wonderwords import RandomWord
    word_source = RandomWord()
except ImportError:
    word_source = None
    logging.warning("wonderwords not installed, using built-in word list")


# MODULE 2: SCORING
def count_correct_chars(target, typed):
    """Number of characters that match the target at the same position."""
    return sum(1 for a, b in zip(target, typed) if a == b)


def calculate_results(target, typed, seconds):
    """
    Input : target text, typed text, time taken in seconds
    Output: dict with wpm, accuracy (%), errors
    WPM uses the standard rule: 5 characters = 1 word.
    """
    if seconds <= 0 or not target:
        return {"wpm": 0.0, "accuracy": 0.0, "errors": len(target)}

    correct = count_correct_chars(target, typed)
    # Missing or extra characters also count as errors
    errors = max(len(target), len(typed)) - correct
    wpm = (correct / 5) / (seconds / 60)
    accuracy = (correct / max(len(target), len(typed), 1)) * 100
    return {"wpm": round(wpm, 1), "accuracy": round(accuracy, 1), "errors": errors}


# MODULE 3: HISTORY (CSV)
def ensure_csv_exists():
    """Create the CSV with headers if it does not exist yet."""
    if not os.path.exists(RESULTS_FILE):
        try:
            with open(RESULTS_FILE, "w", newline="", encoding="utf-8") as f:
                csv.writer(f).writerow(CSV_HEADERS)
            logging.info("Created %s", RESULTS_FILE)
        except OSError as e:
            logging.error("Could not create CSV: %s", e)
            print("Warning: could not create the results file.")


def save_result(mode, results, seconds):
    """Append one test result to the CSV file."""
    ensure_csv_exists()
    row = [
        time.strftime("%Y-%m-%d %H:%M"),
        mode,
        results["wpm"],
        results["accuracy"],
        results["errors"],
        round(seconds, 1),
    ]
    try:
        with open(RESULTS_FILE, "a", newline="", encoding="utf-8") as f:
            csv.writer(f).writerow(row)
        logging.info("Saved result: %s", row)
        print("Result saved.")
    except OSError as e:
        logging.error("Could not save result: %s", e)
        print("Warning: result could not be saved.")


def load_history():
    """Read all valid rows. Corrupt rows are skipped, not fatal."""
    ensure_csv_exists()
    rows = []
    try:
        with open(RESULTS_FILE, newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                try:
                    row["wpm"] = float(row["wpm"])
                    row["accuracy"] = float(row["accuracy"])
                    rows.append(row)
                except (ValueError, KeyError, TypeError):
                    logging.warning("Skipped corrupt row: %s", row)
    except OSError as e:
        logging.error("Could not read CSV: %s", e)
        print("Warning: could not read the results file.")
    return rows


def show_history():
    """Print the last 10 results and the personal best."""
    rows = load_history()
    if not rows:
        print("\nNo results yet. Take a test first!")
        return

    print("\n--- Last 10 results ---")
    print(f"{'Date':<17}{'Mode':<12}{'WPM':>6}{'Acc%':>7}{'Errors':>8}")
    for r in rows[-10:]:
        print(f"{r['date']:<17}{r['mode']:<12}{r['wpm']:>6}{r['accuracy']:>7}{r['errors']:>8}")

    best = max(rows, key=lambda r: r["wpm"])
    avg = sum(r["wpm"] for r in rows) / len(rows)
    print(f"\nPersonal best: {best['wpm']} WPM ({best['date']})")
    print(f"Average WPM  : {avg:.1f} over {len(rows)} tests")


# MODULE 1: TEST ENGINE
def get_choice(prompt, valid):
    """Keep asking until the user enters one of the valid options."""
    while True:
        try:
            choice = input(prompt).strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            raise SystemExit
        if choice in valid:
            return choice
        print(f"Invalid choice. Please enter one of: {', '.join(valid)}")


def countdown():
    print("\nGet ready...")
    for n in (3, 2, 1):
        print(n)
        time.sleep(1)
    print("GO!\n")


def get_random_words(count):
    words = []
    if word_source is not None:
        try:
            candidates = word_source.random_words(count * 2)
            words = [w for w in candidates if w.isalpha()][:count]
        except Exception as e:  # library errors should never crash the test
            logging.error("wonderwords failed: %s", e)
    if len(words) < count:
        words += random.choices(WORDS, k=count - len(words))
    return words


def generate_sentence(word_count):
    return " ".join(get_random_words(word_count)).capitalize() + "."


def get_sentence_length():
    while True:
        try:
            raw = input(f"Words per sentence ({MIN_WORDS}-{MAX_WORDS}): ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nExiting.")
            raise SystemExit
        try:
            n = int(raw)
        except ValueError:
            print("Please enter a whole number.")
            continue
        if MIN_WORDS <= n <= MAX_WORDS:
            return n
        print(f"Please choose between {MIN_WORDS} and {MAX_WORDS}.")


def run_sentence_mode(length):
    target = generate_sentence(length)

    countdown()
    start = time.perf_counter()
    print(target)
    typed = input("> ")
    seconds = time.perf_counter() - start

    results = calculate_results(target, typed, seconds)
    return "sentence", results, seconds


def run_timed_mode(limit, length):
    target_text, typed_text = [], []

    countdown()
    start = time.perf_counter()
    while time.perf_counter() - start < limit:
        sentence = generate_sentence(length)
        print(sentence)
        typed = input("> ")
        target_text.append(sentence)
        typed_text.append(typed)
    seconds = time.perf_counter() - start

    results = calculate_results(" ".join(target_text), " ".join(typed_text), seconds)
    return f"timed-{limit}s", results, seconds


def show_results(results, seconds):
    print("\n========== RESULTS ==========")
    print(f"Speed    : {results['wpm']} WPM")
    print(f"Accuracy : {results['accuracy']} %")
    print(f"Errors   : {results['errors']}")
    print(f"Time     : {seconds:.1f} seconds")
    print("=============================")


def start_test():
    print("\n1. Sentence mode (type one random sentence)")
    print("2. Timed mode (type until time runs out)")
    mode = get_choice("Choose mode (1/2): ", ["1", "2"])

    length = get_sentence_length()

    try:
        if mode == "1":
            name, results, seconds = run_sentence_mode(length)
        else:
            print("\nTime limit: 1) 15s  2) 30s  3) 60s")
            t = get_choice("Choose time (1/2/3): ", list(TIMED_OPTIONS))
            name, results, seconds = run_timed_mode(TIMED_OPTIONS[t], length)
    except (EOFError, KeyboardInterrupt):
        print("\nTest cancelled.")
        logging.info("Test cancelled by user")
        return

    logging.info("Test finished: mode=%s results=%s", name, results)
    show_results(results, seconds)
    save_result(name, results, seconds)


# MAIN WORKFLOW
def main():
    logging.info("Program started")
    print("=== TYPING SPEED TESTER ===")
    while True:
        print("\n1. Start test")
        print("2. View history")
        print("3. Quit")
        choice = get_choice("Choose (1/2/3): ", ["1", "2", "3"])

        if choice == "1":
            start_test()
        elif choice == "2":
            show_history()
        else:
            print("Goodbye!")
            logging.info("Program ended")
            break


if __name__ == "__main__":
    main()