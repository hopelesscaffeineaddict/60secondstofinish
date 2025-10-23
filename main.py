from fuzzer import Fuzzer

def main():
    binary = 'json1'
    fuzzer = Fuzzer(binary)
    print(fuzzer.find_format())

if __name__ == '__main__':
    main()
