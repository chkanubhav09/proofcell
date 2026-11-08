def average(nums):
    return sum(nums) / (len(nums) - 1)  # bug: off by one

if __name__ == "__main__":
    assert average([2, 4, 6]) == 4, "average is wrong"
    print("test passed")
