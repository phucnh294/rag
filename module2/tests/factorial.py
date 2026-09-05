import sys
def factorial(n):
    """
    Tính giai thừa của một số nguyên n.

    Args:
        n: Số nguyên dương để tính giai thừa.

    Returns:
        Giai thừa của n.
    """

    if n == 0:
        return 1
    else:
        return n * factorial(n - 1)

n = int(sys.argv[1])
print(factorial(n))