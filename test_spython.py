import unittest

from spython import SpythonRuntimeError, SpythonSyntaxError, run


class SpythonTests(unittest.TestCase):
    def execute(self, source: str) -> list[str]:
        output: list[str] = []
        run(source, output.append)
        return output

    def test_arithmetic_variables_and_print(self) -> None:
        self.assertEqual(
            self.execute('let total = 2 + 3 * 4 - 1; print("total:", total);'),
            ["total: 13"],
        )

    def test_conditionals_and_loop(self) -> None:
        source = """
        let count = 0;
        while (count < 3) {
            count = count + 1;
        }
        if (count == 3) { print(count); } else { print(0); }
        """
        self.assertEqual(self.execute(source), ["3"])

    def test_functions_and_closures(self) -> None:
        source = """
        let amount = 10;
        fn add_amount(value) { return value + amount; }
        print(add_amount(5));
        """
        self.assertEqual(self.execute(source), ["15"])

    def test_lists_indexing_and_assignment(self) -> None:
        source = """
        let values = [10, [20, 30], true];
        values[1][0] = 25;
        print(values);
        print(values[-1]);
        print("spython"[2]);
        """
        self.assertEqual(
            self.execute(source), ["[10, [25, 30], true]", "true", "y"]
        )

    def test_syntax_and_runtime_errors(self) -> None:
        with self.assertRaises(SpythonSyntaxError):
            run("let x = ;")
        with self.assertRaisesRegex(SpythonRuntimeError, "Undefined variable"):
            run("print(missing);")
        with self.assertRaisesRegex(SpythonRuntimeError, "Index out of range"):
            run("print([1][2]);")
        with self.assertRaisesRegex(SpythonRuntimeError, "Index must be an integer"):
            run('print([1]["zero"]);')


if __name__ == "__main__":
    unittest.main()