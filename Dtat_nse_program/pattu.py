height = 7  # Reduced height for lowercase letter
width = 5   # Adjusted width for 'e'

def printE():
    for i in range(height):
        for j in range(width):
            # Top curve (positions 1,2,3)
            if ((i == 0 or i == height-1) and j > 0 and j < width-1):
                print("*", end="")
            # Middle line (positions 0 to 4)
            elif (i == height//2 and j < width):
                print("*", end="")
            # Left side (position 0)
            elif (i > 0 and i < height-1 and j == 0):
                print("*", end="")
            # Right side (position 4) - only in bottom half
            elif (i > height//2 and i < height-1 and j == width-1):
                print("*", end="")
            else:
                print(" ", end="")
        print()

def printPattern(character):
    if character == 'e':
        printE()

if __name__ == "__main__":
    character = 'e'
    printPattern(character)
