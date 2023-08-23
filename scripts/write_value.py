from scripts.files.fs import write


def main() -> None:
    # store count
    write("/tmp/test/count", str(123).encode())
    


if __name__ == "__main__":
    main()
