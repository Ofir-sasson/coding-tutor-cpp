import random
from typing import List, Dict, Any

# ─────────────── C shared setups ────────────────────────────────────────────
_C_BASE = "#include <stdio.h>\n#include <stdlib.h>"

_LINKED_LIST_SETUP = r"""#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

typedef struct Node {
    int data;
    struct Node* next;
} Node;

/* Reference helpers used by test harness only – do not redefine these */
static Node* _mk(int d){Node* n=malloc(sizeof(Node));n->data=d;n->next=NULL;return n;}
static void  _push(Node** h,int d){Node* n=_mk(d);n->next=*h;*h=n;}
static void  _free(Node* h){Node* t;while(h){t=h->next;free(h);h=t;}}
"""

_FUNC_PTR_SETUP = r"""#include <stdio.h>
#include <stdlib.h>

typedef int  (*Comparator)(const void*, const void*);
typedef int  (*Predicate)(int);
typedef void (*Action)(int);
"""

# ─────────────── C++ shared setups ──────────────────────────────────────────
_CPP_BASE = (
    "#include <iostream>\n"
    "#include <cmath>\n"
    "#include <iomanip>\n"
    "#include <string>\n"
    "#include <sstream>\n"
    "#include <stdexcept>\n"
    "using namespace std;\n"
)

# Shape abstract class — used as setup for Rectangle and total_area parts
_SHAPE_REF = _CPP_BASE + r"""
/* Reference Shape class — do NOT redefine it */
class Shape {
public:
    virtual double area() const = 0;
    virtual double perimeter() const = 0;
    virtual void print() const {
        cout << fixed << setprecision(2)
             << "Shape: area=" << area() << ", perimeter=" << perimeter() << "\n";
    }
    virtual ~Shape() {}
};
"""

# Shape + Circle + Rectangle — used as setup for total_area part
_SHAPE_CIRCLE_RECT_REF = _SHAPE_REF + r"""
/* Reference Circle and Rectangle — do NOT redefine them */
class Circle : public Shape {
    double r;
public:
    Circle(double rad) : r(rad) {}
    double area() const override { return M_PI * r * r; }
    double perimeter() const override { return 2.0 * M_PI * r; }
    void print() const override {
        cout << fixed << setprecision(2)
             << "Circle(r=" << r << "): area=" << area()
             << ", perimeter=" << perimeter() << "\n";
    }
};
class Rectangle : public Shape {
    double w, h;
public:
    Rectangle(double wi, double hi) : w(wi), h(hi) {}
    double area() const override { return w * h; }
    double perimeter() const override { return 2.0 * (w + h); }
    void print() const override {
        cout << fixed << setprecision(2)
             << "Rectangle(" << w << "x" << h << "): area=" << area()
             << ", perimeter=" << perimeter() << "\n";
    }
};
"""

# Dynamic 2D reference implementations — used as setup for fill and transpose parts
_DYNAMIC_2D_REF = _C_BASE + r"""
/* Reference helpers — do NOT redefine alloc_matrix/free_matrix/fill_matrix */
static int** _ref_alloc(int rows, int cols) {
    int** m = (int**)malloc(rows * sizeof(int*));
    for(int i = 0; i < rows; i++) m[i] = (int*)calloc(cols, sizeof(int));
    return m;
}
static void _ref_free(int** m, int rows) {
    for(int i = 0; i < rows; i++) free(m[i]);
    free(m);
}
static void _ref_fill(int** m, int rows, int cols) {
    for(int i = 0; i < rows; i++)
        for(int j = 0; j < cols; j++)
            m[i][j] = i * cols + j;
}
"""

# Shared CHECK macros
_C_CHECK = r"""static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
"""
_CPP_CHECK = r"""static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}
#define NEAR(a,b) (fabs((double)(a)-(double)(b))<0.01)
"""

# ─────────────────────────────────────────────────────────────────────────────
SCENARIOS: List[Dict[str, Any]] = [

    # ───────────── C Topics ─────────────────────────────────────────────────

    {
        "id": "bit_ops",
        "name": "Bit Manipulation in C",
        "dev_requirement": """**Task: Bit Manipulation in C**

Implement the following using **bitwise operators only** (no division, modulo, or loops where not needed):

1. `int count_set_bits(unsigned int n)` — count the number of 1-bits.
   Use **Brian Kernighan's algorithm**: the loop `n &= (n - 1)` clears the lowest set bit.

2. `int is_power_of_two(unsigned int n)` — return 1 if n is a power of 2, 0 otherwise.
   Single expression using `&`. Handle n == 0.

3. `unsigned char swap_nibbles(unsigned char byte)` — swap the upper and lower 4-bit nibbles.
   Example: `0xAB` → `0xBA`

4. `void print_binary(unsigned int n, int bits)` — print n in binary, MSB first, `bits` wide.

Write `main()` that tests all four functions with at least 3 values each, printing input and output clearly.""",
        "requirements": """
- count_set_bits: must use the n &= (n-1) loop
- is_power_of_two: single bitwise expression (n && !(n & (n-1))), handles 0
- swap_nibbles: uses <<4, >>4 and | to combine nibbles
- print_binary: loop with bit shifting and masking
- main: at least 3 test values per function
""",
        "validation_criteria": """
PASS if:
- count_set_bits uses Kernighan's algorithm and handles 0 and UINT_MAX
- is_power_of_two is a single bitwise expression, handles 0 correctly
- swap_nibbles correctly swaps upper/lower 4 bits
- print_binary prints the correct binary representation
- main tests all 4 functions with multiple values

FAIL if:
- Uses division or modulo instead of bitwise ops
- is_power_of_two uses a loop
- swap_nibbles logic is incorrect
""",
        "parts": [
            {
                "part_id": "count_set_bits",
                "title": "count_set_bits",
                "description": (
                    "Implement: `int count_set_bits(unsigned int n)` — count the number of 1-bits in `n`.\n\n"
                    "**Use Brian Kernighan's algorithm:** the loop `n &= (n - 1)` clears the lowest set bit each iteration.\n\n"
                    "Write only the function — no `main()`."
                ),
                "setup": "#include <stdio.h>",
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    CHECK(count_set_bits(0)==0,          "0 -> 0 bits");
    CHECK(count_set_bits(1)==1,          "1 -> 1 bit");
    CHECK(count_set_bits(7)==3,          "7=0b111 -> 3 bits");
    CHECK(count_set_bits(0xFF)==8,       "0xFF -> 8 bits");
    CHECK(count_set_bits(0xFFFFFFFF)==32,"all-ones -> 32 bits");
    CHECK(count_set_bits(0b10110100)==4, "0b10110100 -> 4 bits");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "is_power_of_two",
                "title": "is_power_of_two",
                "description": (
                    "Implement: `int is_power_of_two(unsigned int n)` — return **1** if `n` is a power of 2, **0** otherwise.\n\n"
                    "**Key insight:** a power of two has exactly one 1-bit. Use a single bitwise expression.\n"
                    "Handle the edge case `n == 0` (0 is NOT a power of two).\n\n"
                    "Write only the function — no `main()`."
                ),
                "setup": "#include <stdio.h>",
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    CHECK(is_power_of_two(0)==0,    "0 is NOT power of two");
    CHECK(is_power_of_two(1)==1,    "1 IS power of two");
    CHECK(is_power_of_two(2)==1,    "2 IS power of two");
    CHECK(is_power_of_two(4)==1,    "4 IS power of two");
    CHECK(is_power_of_two(16)==1,   "16 IS power of two");
    CHECK(is_power_of_two(1024)==1, "1024 IS power of two");
    CHECK(is_power_of_two(3)==0,    "3 is NOT power of two");
    CHECK(is_power_of_two(6)==0,    "6 is NOT power of two");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "swap_nibbles",
                "title": "swap_nibbles",
                "description": (
                    "Implement: `unsigned char swap_nibbles(unsigned char byte)` — swap the upper and lower 4-bit nibbles.\n\n"
                    "Example: `0xAB` (upper=A, lower=B) → `0xBA`\n\n"
                    "**Hint:** shift right by 4, shift left by 4, combine with `|`.\n\n"
                    "Write only the function — no `main()`."
                ),
                "setup": "#include <stdio.h>",
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    CHECK(swap_nibbles(0xAB)==0xBA, "0xAB -> 0xBA");
    CHECK(swap_nibbles(0x12)==0x21, "0x12 -> 0x21");
    CHECK(swap_nibbles(0x00)==0x00, "0x00 -> 0x00");
    CHECK(swap_nibbles(0xFF)==0xFF, "0xFF -> 0xFF");
    CHECK(swap_nibbles(0xF0)==0x0F, "0xF0 -> 0x0F");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "print_binary",
                "title": "print_binary",
                "description": (
                    "Implement: `void print_binary(unsigned int n, int bits)` — print `n` in binary (MSB first), exactly `bits` digits wide.\n\n"
                    "Example: `print_binary(5, 8)` → prints `00000101`\n\n"
                    "**Hint:** loop from bit `bits-1` down to 0, extract each bit with `(n >> i) & 1`.\n\n"
                    "Write only the function — no `main()`."
                ),
                "setup": "#include <stdio.h>\n#include <string.h>\n#include <unistd.h>",
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}

static void _capture(unsigned int n, int bits, char* out, int sz){
    int pfd[2]; pipe(pfd);
    int sv = dup(STDOUT_FILENO);
    dup2(pfd[1], STDOUT_FILENO);
    print_binary(n, bits);
    fflush(stdout);
    dup2(sv, STDOUT_FILENO);
    close(pfd[1]); close(sv);
    int r = (int)read(pfd[0], out, sz-1);
    out[r>0?r:0]='\0';
    close(pfd[0]);
    int l=strlen(out);
    while(l>0&&(out[l-1]=='\n'||out[l-1]==' '||out[l-1]=='\r')) out[--l]='\0';
}

int main(void){
    char buf[128];
    _capture(5,  8, buf, sizeof(buf)); CHECK(strcmp(buf,"00000101")==0, "5 in 8 bits = 00000101");
    _capture(255,8, buf, sizeof(buf)); CHECK(strcmp(buf,"11111111")==0, "255 in 8 bits = 11111111");
    _capture(0,  4, buf, sizeof(buf)); CHECK(strcmp(buf,"0000")==0,     "0 in 4 bits = 0000");
    _capture(10, 4, buf, sizeof(buf)); CHECK(strcmp(buf,"1010")==0,     "10 in 4 bits = 1010");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
        ],
    },

    {
        "id": "strings_no_lib",
        "name": "String Utilities Without <string.h>",
        "accumulate_code": True,
        "dev_requirement": """**Task: String Utility Functions in C — WITHOUT <string.h>**

Implement all five from scratch. Do NOT use `strlen`, `strcpy`, `strcat`, `strcmp`, or any other `<string.h>` function.

1. `int my_strlen(const char* s)` — returns length, excluding null terminator
2. `void my_strcpy(char* dest, const char* src)` — copies src into dest, including `\\0`
3. `void my_strrev(char* s)` — reverses string **IN-PLACE** using two-pointer technique
4. `int my_strcmp(const char* a, const char* b)` — returns 0 if equal, <0 or >0 otherwise
5. `char* my_strdup(const char* s)` — malloc a copy; caller is responsible for freeing

Write `main()` testing each function with at least 2 cases, including edge cases: empty string `""` and single character `"a"`.""",
        "requirements": """
- No <string.h> imports at all
- my_strrev: two-pointer swap (i from start, j from end, while i < j)
- my_strdup: malloc(my_strlen(s) + 1) bytes, copy all including null terminator
- my_strcmp: character-by-character difference comparison
- Edge cases tested: "", "a"
""",
        "validation_criteria": """
PASS if:
- All 5 functions work correctly without any string.h function
- my_strrev uses in-place two-pointer swap
- my_strdup allocates exactly strlen+1 bytes and copies the null terminator
- Edge cases demonstrated in main

FAIL if:
- Any string.h function used
- my_strrev uses a temporary buffer instead of in-place
- my_strdup forgets +1 for null terminator
- No edge case testing
""",
        "parts": [
            {
                "part_id": "my_strlen",
                "title": "my_strlen",
                "description": (
                    "Implement: `int my_strlen(const char* s)` — returns the number of characters before the null terminator `\\0`.\n\n"
                    "**Do NOT use any `<string.h>` functions.** Use pointer traversal.\n\n"
                    "Write only the function — no `main()`."
                ),
                "setup": _C_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    CHECK(my_strlen("")==0,           "empty string -> 0");
    CHECK(my_strlen("a")==1,          "single char -> 1");
    CHECK(my_strlen("hello")==5,      "hello -> 5");
    CHECK(my_strlen("hello world")==11,"hello world -> 11");
    CHECK(my_strlen("abc")==3,        "abc -> 3");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "my_strcpy",
                "title": "my_strcpy",
                "description": (
                    "Implement: `void my_strcpy(char* dest, const char* src)` — copies all characters from `src` to `dest`, **including the null terminator** `\\0`.\n\n"
                    "**Do NOT use any `<string.h>` functions.** Use pointer traversal.\n\n"
                    "Write only the function — no `main()`."
                ),
                "setup": _C_BASE,
                "test_harness": r"""
#include <string.h>
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    char buf[100];
    my_strcpy(buf, "hello");
    CHECK(strcmp(buf,"hello")==0,   "copy hello");
    my_strcpy(buf, "");
    CHECK(buf[0]=='\0',             "copy empty string");
    my_strcpy(buf, "a");
    CHECK(strcmp(buf,"a")==0,       "copy single char");
    my_strcpy(buf, "abc 123!");
    CHECK(strcmp(buf,"abc 123!")==0,"copy with spaces");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "my_strrev",
                "title": "my_strrev",
                "description": (
                    "Implement: `void my_strrev(char* s)` — reverses the string **in-place** using the two-pointer technique.\n\n"
                    "**Algorithm:** use two indices — `i` starting at 0 and `j` starting at `strlen(s)-1`. While `i < j`, swap `s[i]` and `s[j]`, then move both inward.\n\n"
                    "**Do NOT use any `<string.h>` functions** (you can compute the length yourself with a loop). Write only the function — no `main()`."
                ),
                "setup": _C_BASE,
                "test_harness": r"""
#include <string.h>
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    char s1[]="hello"; my_strrev(s1); CHECK(strcmp(s1,"olleh")==0, "hello -> olleh");
    char s2[]="a";     my_strrev(s2); CHECK(strcmp(s2,"a")==0,     "single char unchanged");
    char s3[]="";      my_strrev(s3); CHECK(s3[0]=='\0',           "empty unchanged");
    char s4[]="ab";    my_strrev(s4); CHECK(strcmp(s4,"ba")==0,    "ab -> ba");
    char s5[]="abcde"; my_strrev(s5); CHECK(strcmp(s5,"edcba")==0, "abcde -> edcba");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "my_strcmp",
                "title": "my_strcmp",
                "description": (
                    "Implement: `int my_strcmp(const char* a, const char* b)` — compares two strings lexicographically.\n\n"
                    "Returns: **0** if equal, **negative** if `a < b`, **positive** if `a > b`.\n\n"
                    "Compare character by character; when they differ, return the difference `(*a - *b)`.\n\n"
                    "**Do NOT use any `<string.h>` functions.** Write only the function — no `main()`."
                ),
                "setup": "#include <stdio.h>",
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
#define SIGN(x) ((x)>0?1:(x)<0?-1:0)
int main(void){
    CHECK(my_strcmp("","") == 0,              "both empty -> 0");
    CHECK(my_strcmp("a","a") == 0,            "equal single char -> 0");
    CHECK(my_strcmp("hello","hello") == 0,    "equal strings -> 0");
    CHECK(SIGN(my_strcmp("a","b")) < 0,       "a < b -> negative");
    CHECK(SIGN(my_strcmp("b","a")) > 0,       "b > a -> positive");
    CHECK(SIGN(my_strcmp("abc","abd")) < 0,   "abc < abd");
    CHECK(SIGN(my_strcmp("ab","abc")) < 0,    "shorter < longer");
    CHECK(SIGN(my_strcmp("abc","ab")) > 0,    "longer > shorter");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "my_strdup",
                "title": "my_strdup",
                "description": (
                    "Implement: `char* my_strdup(const char* s)` — allocates memory with `malloc()` and returns a full copy of `s`.\n\n"
                    "The caller is responsible for `free()`-ing the returned pointer.\n\n"
                    "**Tip:** you need the length to know how many bytes to `malloc`. You can include your own `my_strlen` implementation or compute the length with a pointer loop.\n\n"
                    "**Do NOT use any `<string.h>` functions.** Write the function(s) you need — no `main()`."
                ),
                "setup": _C_BASE,
                "test_harness": r"""
#include <string.h>
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    char* d;
    d = my_strdup("hello");
    CHECK(d!=NULL,                 "not null for hello");
    CHECK(strcmp(d,"hello")==0,    "hello content correct");
    free(d);
    d = my_strdup("");
    CHECK(d!=NULL,                 "not null for empty");
    CHECK(d[0]=='\0',              "empty content correct");
    free(d);
    d = my_strdup("a");
    CHECK(d!=NULL,                 "not null for single char");
    CHECK(strcmp(d,"a")==0,        "single char content");
    free(d);
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
        ],
    },

    {
        "id": "pointer_arithmetic",
        "name": "Pointer Arithmetic in C",
        "dev_requirement": """**Task: Array Operations Using Only Pointer Arithmetic**

You are **NOT allowed** to use array subscript notation `a[i]`. All array access must use pointer arithmetic: `*(ptr + i)` or pointer increment.

Implement:
1. `int find_max(int* arr, int n)` — return the maximum element using pointer traversal
2. `void reverse_array(int* arr, int n)` — reverse in-place using two pointers (left/right)
3. `int* matrix_row(int* matrix, int cols, int row)` — return a pointer to the start of the given row in a flat 2D array
4. `void print_matrix(int* matrix, int rows, int cols)` — print a 2D matrix (stored flat), using only pointer arithmetic

Write `main()` that:
- Creates an int array, tests `find_max` and `reverse_array`
- Creates a 3×4 flat matrix, uses `matrix_row` and `print_matrix`""",
        "requirements": """
- NO [ ] subscript syntax anywhere in the implementation
- All access via *(ptr + offset) or pointer increment
- reverse_array: two-pointer swap with a temp variable
- matrix_row: returns ptr + row * cols
- print_matrix: nested pointer-arithmetic loops
""",
        "validation_criteria": """
PASS if:
- No [ ] indexing used anywhere in the functions
- find_max traverses with pointer arithmetic
- reverse_array correctly reverses using two pointer approach
- matrix_row returns the correct pointer offset (row * cols)
- print_matrix prints correct rows/cols

FAIL if:
- Uses [ ] subscript notation
- Incorrect pointer arithmetic for matrix indexing
""",
        "parts": [
            {
                "part_id": "find_max_reverse",
                "title": "find_max + reverse_array",
                "description": (
                    "**Do NOT use `arr[i]` — use pointer arithmetic only** (`*(arr + i)` or pointer increment).\n\n"
                    "Implement:\n\n"
                    "1. `int find_max(int* arr, int n)` — traverse with a pointer and return the maximum element.\n\n"
                    "2. `void reverse_array(int* arr, int n)` — reverse the array **in-place** using two pointers: "
                    "one starting at the beginning, one at the end, swapping and moving inward.\n\n"
                    "Write only these 2 functions — no `main()`."
                ),
                "setup": _C_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    int a1[]={3,1,7,2,9,4};
    CHECK(find_max(a1,6)==9,  "find_max {3,1,7,2,9,4}=9");
    int a2[]={-5,-1,-3};
    CHECK(find_max(a2,3)==-1, "find_max negatives=-1");
    int a3[]={42};
    CHECK(find_max(a3,1)==42, "find_max single=42");
    int a4[]={1,1,1};
    CHECK(find_max(a4,3)==1,  "find_max all-same=1");

    int r1[]={1,2,3,4,5};
    reverse_array(r1,5);
    CHECK(*(r1+0)==5&&*(r1+1)==4&&*(r1+2)==3&&*(r1+3)==2&&*(r1+4)==1,
          "reverse {1,2,3,4,5}");
    int r2[]={7};
    reverse_array(r2,1);
    CHECK(*r2==7, "reverse single unchanged");
    int r3[]={1,2};
    reverse_array(r3,2);
    CHECK(*r3==2&&*(r3+1)==1, "reverse {1,2}={2,1}");

    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "matrix_row",
                "title": "matrix_row + print_matrix",
                "description": (
                    "A 2D matrix is stored **flat** in memory: `int mat[rows*cols]`. Row `i` starts at `mat + i*cols`.\n\n"
                    "**Do NOT use `[ ]` — use pointer arithmetic only.**\n\n"
                    "Implement:\n\n"
                    "1. `int* matrix_row(int* matrix, int cols, int row)` — return a pointer to the first element of the given row.\n\n"
                    "2. `void print_matrix(int* matrix, int rows, int cols)` — print the matrix row by row. "
                    "Each row on its own line, values separated by spaces.\n\n"
                    "Write only these 2 functions — no `main()`."
                ),
                "setup": _C_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    int mat[12]={1,2,3,4, 5,6,7,8, 9,10,11,12};
    int* r0 = matrix_row(mat, 4, 0);
    int* r1 = matrix_row(mat, 4, 1);
    int* r2 = matrix_row(mat, 4, 2);
    CHECK(r0 == mat,      "row0 pointer = mat start");
    CHECK(r1 == mat + 4,  "row1 pointer = mat+4");
    CHECK(r2 == mat + 8,  "row2 pointer = mat+8");
    CHECK(*r0 == 1,       "mat[0][0] = 1");
    CHECK(*r1 == 5,       "mat[1][0] = 5");
    CHECK(*(r1+2) == 7,   "mat[1][2] = 7");
    CHECK(*(r2+3) == 12,  "mat[2][3] = 12");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
        ],
    },

    {
        "id": "dynamic_2d_array",
        "name": "Dynamic 2D Array in C",
        "dev_requirement": """**Task: Dynamically Allocated 2D Matrix in C**

Implement a 2D integer matrix as an array of pointers:

1. `int** alloc_matrix(int rows, int cols)` — allocate `rows` pointers (with `malloc`), each pointing to a malloc'd row of `cols` ints. Zero-initialize all cells.

2. `void free_matrix(int** m, int rows)` — free each row first, then free the pointer array.

3. `void fill_matrix(int** m, int rows, int cols)` — set `m[i][j] = i * cols + j`

4. `int** transpose(int** m, int rows, int cols)` — allocate and return a NEW transposed matrix (`cols x rows`). Caller must free it. Copy `m[i][j]` → `t[j][i]`.

5. `void print_matrix(int** m, int rows, int cols)` — print formatted.

Write `main()`:
- Allocate a 3×4 matrix, fill it, print it
- Compute and print its 4×3 transpose
- Free both matrices""",
        "requirements": """
- alloc_matrix: malloc(rows * sizeof(int*)) then malloc(cols * sizeof(int)) per row
- free_matrix: free each row first, then free the pointer array
- transpose: allocate new int** of [cols][rows], copy m[i][j] to t[j][i]
- All allocated memory freed in main (no leaks)
""",
        "validation_criteria": """
PASS if:
- alloc_matrix correctly allocates pointer array and each row
- free_matrix frees each row then the pointer array
- transpose allocates new matrix and correctly swaps indices
- main allocates, fills, prints original and transposed, frees both

FAIL if:
- Memory leak (rows or pointer array not freed)
- Incorrect transpose indexing (m[i][j] → t[i][j] instead of t[j][i])
- Missing free in main
""",
        "parts": [
            {
                "part_id": "alloc_free",
                "title": "alloc_matrix + free_matrix",
                "description": (
                    "Implement a dynamic 2D integer matrix using an **array of pointers**.\n\n"
                    "1. `int** alloc_matrix(int rows, int cols)` — allocate `rows` pointers with `malloc`, "
                    "each pointing to a `calloc`'d row of `cols` ints. All cells must be **zero-initialized**.\n\n"
                    "2. `void free_matrix(int** m, int rows)` — free **each row** first, then free the pointer array. "
                    "Do NOT free the rows first without freeing the pointer array — that leaks.\n\n"
                    "Write only these 2 functions — no `main()`."
                ),
                "setup": _C_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    int** mat = alloc_matrix(3, 4);
    CHECK(mat != NULL, "alloc_matrix 3x4 not NULL");
    int zero_ok = 1;
    for(int i=0;i<3;i++) for(int j=0;j<4;j++) if(mat[i][j]!=0) zero_ok=0;
    CHECK(zero_ok, "all cells zero-initialized");
    free_matrix(mat, 3);

    int** m2 = alloc_matrix(1, 1);
    CHECK(m2 != NULL,    "1x1 matrix not NULL");
    CHECK(m2[0][0]==0,   "1x1 cell zero");
    m2[0][0] = 99;
    CHECK(m2[0][0]==99,  "1x1 cell writeable");
    free_matrix(m2, 1);

    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "fill_matrix",
                "title": "fill_matrix + print_matrix",
                "description": (
                    "Reference implementations of `alloc_matrix` and `free_matrix` are provided — "
                    "you do **not** need to implement them here.\n\n"
                    "Implement:\n\n"
                    "1. `void fill_matrix(int** m, int rows, int cols)` — set every cell so that `m[i][j] = i * cols + j`.\n\n"
                    "2. `void print_matrix(int** m, int rows, int cols)` — print each row on its own line, "
                    "values separated by a single space.\n\n"
                    "Write only these 2 functions — no `main()`."
                ),
                "setup": _DYNAMIC_2D_REF,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    int** m = _ref_alloc(3, 4);
    fill_matrix(m, 3, 4);
    CHECK(m[0][0]==0,  "m[0][0]=0*4+0=0");
    CHECK(m[0][1]==1,  "m[0][1]=0*4+1=1");
    CHECK(m[0][3]==3,  "m[0][3]=0*4+3=3");
    CHECK(m[1][0]==4,  "m[1][0]=1*4+0=4");
    CHECK(m[1][2]==6,  "m[1][2]=1*4+2=6");
    CHECK(m[2][0]==8,  "m[2][0]=2*4+0=8");
    CHECK(m[2][3]==11, "m[2][3]=2*4+3=11");
    _ref_free(m, 3);
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "transpose",
                "title": "transpose",
                "description": (
                    "Reference implementations of `alloc_matrix`, `free_matrix`, and `fill_matrix` are provided.\n\n"
                    "Implement:\n\n"
                    "`int** transpose(int** m, int rows, int cols)` — allocate and return a **new** matrix of size `cols × rows`. "
                    "For every element in `m`, set `t[j][i] = m[i][j]`.\n\n"
                    "The caller is responsible for freeing the returned matrix.\n\n"
                    "Write only this function — no `main()`."
                ),
                "setup": _DYNAMIC_2D_REF,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    int** m = _ref_alloc(3, 4);
    _ref_fill(m, 3, 4);   /* m[i][j] = i*4+j */

    int** t = transpose(m, 3, 4);  /* result is 4x3 */
    CHECK(t != NULL, "transpose not NULL");

    int ok = 1;
    for(int i=0;i<3;i++)
        for(int j=0;j<4;j++)
            if(t[j][i] != m[i][j]) ok=0;
    CHECK(ok, "t[j][i] == m[i][j] for all i,j");

    /* spot checks */
    CHECK(t[0][0]==0,  "t[0][0]=m[0][0]=0");
    CHECK(t[1][0]==1,  "t[1][0]=m[0][1]=1");
    CHECK(t[3][2]==11, "t[3][2]=m[2][3]=11");

    _ref_free(m, 3);
    _ref_free(t, 4);
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
        ],
    },

    {
        "id": "file_io",
        "name": "File I/O in C",
        "dev_requirement": """**Task: File Operations in C**

Write a C program that:

1. **Reads** a text file of integers (one per line) from a filename given as `argv[1]`
2. **Stores** them in a dynamically allocated array — use `realloc` to grow as needed (start with capacity 4, double when full)
3. **Sorts** the array ascending — implement **selection sort** yourself (no `qsort`)
4. **Writes** the sorted integers to `argv[2]` (output file), with this header:
   ```
   Sorted (N values):
   1
   3
   7
   ```
5. **Prints** min, max, and average to stdout

Handle errors:
- If argc < 3: print usage message and `exit(1)`
- If input file cannot be opened: print error and `exit(1)`
- Close all files and free all memory before exiting""",
        "requirements": """
- argc/argv validation (argc < 3 → error)
- fopen/fclose for both input and output files
- fscanf to read integers one by one
- realloc to grow array (start capacity=4, double when full)
- Implement selection sort (not qsort or bubble sort)
- fprintf to write sorted output with header line "Sorted (N values):"
- Error handling for fopen failure
- Free array and close files before exit
""",
        "validation_criteria": """
PASS if:
- Validates argc and prints usage if wrong
- Reads integers from file using fopen/fscanf
- Uses realloc to grow dynamically (not fixed array)
- Implements a correct selection sort
- Writes header + sorted numbers to output file
- Handles fopen failure with error message + exit(1)
- Frees memory and closes both files

FAIL if:
- Fixed-size array instead of realloc
- Uses qsort instead of implementing sort
- No error handling for fopen
- Files not closed or memory not freed
""",
    },

    {
        "id": "func_pointers",
        "name": "Function Pointers in C",
        "dev_requirement": """**Task: Generic Operations Using Function Pointers**

Define these typedefs:
```c
typedef int (*Comparator)(const void*, const void*);
typedef int (*Predicate)(int);
typedef void (*Action)(int);
```

Implement:
1. `void my_sort(int* arr, int n, Comparator cmp)` — bubble sort using the comparator
2. `int count_if(int* arr, int n, Predicate pred)` — count elements satisfying pred
3. `void my_foreach(int* arr, int n, Action action)` — apply action to each element

Then implement these concrete functions to pass as arguments:
- `int cmp_asc(const void* a, const void* b)` — ascending (returns negative if *a < *b)
- `int cmp_desc(const void* a, const void* b)` — descending
- `int is_even(int x)` — 1 if even
- `int is_positive(int x)` — 1 if > 0
- `void print_elem(int x)` — prints the element followed by space

Write `main()` that demonstrates: ascending sort, descending sort, count_if with both predicates, foreach.""",
        "requirements": """
- Correct typedef for all three function pointer types
- my_sort: bubble sort, comparator called as cmp(&arr[i], &arr[j])
- count_if: calls pred for each element, counts trues
- my_foreach: calls action for each element
- Comparators cast void* to int* before dereferencing
- main demonstrates all 5 concrete functions
""",
        "validation_criteria": """
PASS if:
- All three typedefs correct
- my_sort passes pointers to comparator: cmp(&arr[i], &arr[j])
- count_if correctly counts matching elements
- my_foreach correctly applies action
- void* correctly cast to int* in comparators
- main demonstrates ascending and descending sort, both predicates, foreach

FAIL if:
- Function pointers not used (hardcoded logic)
- Incorrect void* casting in comparators
- my_sort passes values instead of pointers to comparator
""",
        "parts": [
            {
                "part_id": "my_sort",
                "title": "my_sort + comparators",
                "description": (
                    "Implement the following (the typedefs are provided for you):\n\n"
                    "1. `void my_sort(int* arr, int n, Comparator cmp)` — bubble sort. "
                    "Call the comparator as `cmp(&arr[i], &arr[j])` (pass **pointers**, not values).\n\n"
                    "2. `int cmp_asc(const void* a, const void* b)` — returns negative if `*a < *b` (ascending order).\n\n"
                    "3. `int cmp_desc(const void* a, const void* b)` — returns negative if `*a > *b` (descending order).\n\n"
                    "**Reminder:** inside comparators, cast `(const int*)a` to dereference.\n\n"
                    "Write only these 3 functions — no `main()`."
                ),
                "setup": _FUNC_PTR_SETUP,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
int main(void){
    int arr1[]={5,2,8,1,9,3}; int n=6;
    my_sort(arr1,n,cmp_asc);
    CHECK(arr1[0]==1&&arr1[1]==2&&arr1[2]==3, "asc: first 3 = 1,2,3");
    CHECK(arr1[3]==5&&arr1[4]==8&&arr1[5]==9, "asc: last 3 = 5,8,9");

    int arr2[]={5,2,8,1,9,3};
    my_sort(arr2,n,cmp_desc);
    CHECK(arr2[0]==9&&arr2[1]==8&&arr2[2]==5, "desc: first 3 = 9,8,5");
    CHECK(arr2[3]==3&&arr2[4]==2&&arr2[5]==1, "desc: last 3 = 3,2,1");

    int arr3[]={42};
    my_sort(arr3,1,cmp_asc);
    CHECK(arr3[0]==42, "single element unchanged");

    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "count_if_foreach",
                "title": "count_if + my_foreach + predicates",
                "description": (
                    "Implement (typedefs are provided for you):\n\n"
                    "1. `int count_if(int* arr, int n, Predicate pred)` — count elements where `pred(elem)` returns non-zero.\n\n"
                    "2. `void my_foreach(int* arr, int n, Action action)` — call `action(elem)` for every element.\n\n"
                    "3. `int is_even(int x)` — return 1 if `x` is even, 0 otherwise.\n\n"
                    "4. `int is_positive(int x)` — return 1 if `x > 0`, 0 otherwise.\n\n"
                    "5. `void print_elem(int x)` — print `x` followed by a space.\n\n"
                    "Write only these 5 functions — no `main()`."
                ),
                "setup": _FUNC_PTR_SETUP,
                "test_harness": r"""
static int _ok=1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}
static int _cnt=0;
static void _count_calls(int x){_cnt++;(void)x;}
int main(void){
    int arr[]={1,-2,3,-4,5,0}; int n=6;
    /* is_even: -2, -4, 0 are even -> 3 */
    CHECK(count_if(arr,n,is_even)==3,    "count even: 3");
    /* is_positive: 1,3,5 -> 3 */
    CHECK(count_if(arr,n,is_positive)==3,"count positive: 3");
    /* empty array */
    CHECK(count_if(arr,0,is_even)==0,    "empty array -> 0");
    /* my_foreach calls action n times */
    _cnt=0; my_foreach(arr,n,_count_calls);
    CHECK(_cnt==n, "my_foreach calls action n=6 times");
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
        ],
    },

    {
        "id": "linked_list",
        "name": "Singly Linked List in C",
        "accumulate_code": True,
        "dev_requirement": """**Task: Singly Linked List in C**

Given:
```c
typedef struct Node {
    int data;
    struct Node* next;
} Node;
```

Implement:
1. `Node* create_node(int data)` — malloc and initialize
2. `void insert_at_head(Node** head, int data)` — insert at beginning
3. `void insert_at_tail(Node** head, int data)` — traverse to end, insert there
4. `void delete_node(Node** head, int target)` — delete first occurrence of target
5. `int list_length(Node* head)` — count nodes
6. `void print_list(Node* head)` — print as `1 -> 2 -> 3 -> NULL`
7. `void free_list(Node* head)` — free all nodes

Write `main()` demonstrating all 7 functions, including deletion of head, middle, and tail nodes.""",
        "requirements": """
- malloc/free for all dynamic memory
- Double pointer (Node**) for insert_at_head, insert_at_tail, delete_node
- delete_node handles: empty list, not found, head deletion, middle/tail
- free_list frees every node without leaks
""",
        "validation_criteria": """
PASS if:
- create_node uses malloc, sets next=NULL
- insert_at_head and insert_at_tail use Node** correctly
- delete_node handles head deletion, middle, and not-found cases
- list_length traverses and counts correctly
- free_list frees all nodes
- main demonstrates all 7 functions including all delete cases

FAIL if:
- Missing double pointer for head modification
- Memory not freed
- delete_node crashes on empty list or not-found
""",
        "parts": [
            {
                "part_id": "create_insert_head_print",
                "title": "create_node + insert_at_head + print_list",
                "description": (
                    "The `Node` struct is already defined for you. Implement:\n\n"
                    "1. `Node* create_node(int data)` — allocate a new node with `malloc`, set `data` and `next = NULL`, return the pointer.\n\n"
                    "2. `void insert_at_head(Node** head, int data)` — create a new node and link it at the **beginning** of the list. Update `*head`.\n\n"
                    "3. `void print_list(Node* head)` — traverse and print in format: `1 -> 2 -> 3 -> NULL` (each node followed by ` -> `, ending with `NULL`).\n\n"
                    "Write only these 3 functions — no `main()`."
                ),
                "setup": _LINKED_LIST_SETUP,
                "test_harness": r"""
static int _ok=1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}

int main(void){
    /* create_node */
    Node* n = create_node(42);
    CHECK(n!=NULL,      "create_node: not null");
    CHECK(n->data==42,  "create_node: data=42");
    CHECK(n->next==NULL,"create_node: next=NULL");
    free(n);

    /* insert_at_head */
    Node* head=NULL;
    insert_at_head(&head,3);
    insert_at_head(&head,2);
    insert_at_head(&head,1);
    CHECK(head->data==1,               "head=1 (last inserted)");
    CHECK(head->next->data==2,         "second=2");
    CHECK(head->next->next->data==3,   "third=3");
    CHECK(head->next->next->next==NULL,"ends with NULL");

    /* print_list via pipe */
    int pfd[2]; pipe(pfd);
    int sv=dup(STDOUT_FILENO);
    dup2(pfd[1],STDOUT_FILENO); print_list(head); fflush(stdout);
    dup2(sv,STDOUT_FILENO); close(pfd[1]); close(sv);
    char buf[256]={0}; int r=read(pfd[0],buf,sizeof(buf)-1);
    buf[r>0?r:0]='\0'; close(pfd[0]);
    CHECK(strstr(buf,"1")&&strstr(buf,"->")&&strstr(buf,"NULL"),
          "print_list contains '1', '->', 'NULL'");

    _free(head);
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "insert_at_tail",
                "title": "insert_at_tail",
                "description": (
                    "The `Node` struct is already defined for you. Implement:\n\n"
                    "`void insert_at_tail(Node** head, int data)` — traverse to the **end** of the list and insert a new node there. If the list is empty, the new node becomes the head.\n\n"
                    "Write only this function — no `main()`."
                ),
                "setup": _LINKED_LIST_SETUP,
                "test_harness": r"""
static int _ok=1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}

int main(void){
    Node* head=NULL;

    /* append to empty list */
    insert_at_tail(&head,1);
    CHECK(head!=NULL,      "first append: head not null");
    CHECK(head->data==1,   "first node data=1");
    CHECK(head->next==NULL,"single node next=NULL");

    /* append more */
    insert_at_tail(&head,2);
    insert_at_tail(&head,3);
    CHECK(head->data==1,               "head still 1");
    CHECK(head->next->data==2,         "second=2");
    CHECK(head->next->next->data==3,   "third=3");
    CHECK(head->next->next->next==NULL,"ends with NULL");

    _free(head);
    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "list_length",
                "title": "list_length",
                "description": (
                    "The `Node` struct is already defined for you. Implement:\n\n"
                    "`int list_length(Node* head)` — traverse the list and return the number of nodes.\n\n"
                    "Return **0** for an empty list (`head == NULL`).\n\n"
                    "Write only this function — no `main()`."
                ),
                "setup": _LINKED_LIST_SETUP,
                "test_harness": r"""
static int _ok=1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}

int main(void){
    /* empty list */
    CHECK(list_length(NULL)==0,"empty list -> 0");

    /* 3-node list */
    Node* h=NULL; _push(&h,3); _push(&h,2); _push(&h,1);
    CHECK(list_length(h)==3,"3-node list -> 3");

    /* single node */
    Node* s=_mk(99);
    CHECK(list_length(s)==1,"single node -> 1");
    free(s); _free(h);

    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
            {
                "part_id": "delete_free",
                "title": "delete_node + free_list",
                "description": (
                    "The `Node` struct is already defined for you. Implement:\n\n"
                    "1. `void delete_node(Node** head, int target)` — remove the **first** node with `data == target`. Handle: empty list, not found, deleting the head, deleting a middle/tail node. Do **not** crash on any case.\n\n"
                    "2. `void free_list(Node* head)` — free **every** node in the list (traverse and `free` each one).\n\n"
                    "Write only these 2 functions — no `main()`."
                ),
                "setup": _LINKED_LIST_SETUP,
                "test_harness": r"""
static int _ok=1;
#define CHECK(c,m) if(!(c)){fprintf(stderr,"FAIL: %s\n",m);_ok=0;}

int main(void){
    Node* h;

    /* delete head */
    h=NULL; _push(&h,3); _push(&h,2); _push(&h,1);
    delete_node(&h,1);
    CHECK(h->data==2,"delete head: new head=2");
    free_list(h);

    /* delete middle */
    h=NULL; _push(&h,3); _push(&h,2); _push(&h,1);
    delete_node(&h,2);
    CHECK(h->data==1 && h->next->data==3,"delete middle: 2 removed");
    free_list(h);

    /* delete tail */
    h=NULL; _push(&h,3); _push(&h,2); _push(&h,1);
    delete_node(&h,3);
    CHECK(h->next->next==NULL,"delete tail: now 2 nodes");
    free_list(h);

    /* not found - must not crash */
    h=NULL; _push(&h,2); _push(&h,1);
    delete_node(&h,99);
    CHECK(h->data==1 && h->next->data==2,"not found: list unchanged");
    free_list(h);

    /* empty list - must not crash */
    h=NULL; delete_node(&h,1);
    CHECK(h==NULL,"empty list stays NULL");

    if(_ok) printf("ALL_PASS\n");
    return _ok?0:1;
}
""",
            },
        ],
    },

    # ───────────── C++ Topics ────────────────────────────────────────────────

    {
        "id": "cpp_class_inherit",
        "name": "C++ Classes and Inheritance",
        "dev_requirement": """**Task: Shape Class Hierarchy in C++**

Implement:

```cpp
class Shape {
public:
    virtual double area() const = 0;
    virtual double perimeter() const = 0;
    virtual void print() const;   // prints: "Shape: area=X, perimeter=Y"
    virtual ~Shape() {}
};

class Circle : public Shape {
    double radius;
public:
    Circle(double r);
    double area() const override;       // M_PI * r * r
    double perimeter() const override;  // 2 * M_PI * r
    void print() const override;        // "Circle(r=X): area=Y, perimeter=Z"
};

class Rectangle : public Shape {
    double width, height;
public:
    Rectangle(double w, double h);
    double area() const override;       // width * height
    double perimeter() const override;  // 2 * (width + height)
    void print() const override;        // "Rectangle(WxH): area=Y, perimeter=Z"
};
```

Write also:
- `double total_area(Shape** shapes, int n)` — sum areas via polymorphism

Write `main()`:
- Create a Circle and Rectangle, store as `Shape*` array
- Call `print()` on each via base pointer (demonstrating polymorphism)
- Call `total_area` and print the result
- Delete the objects (destructor should trigger)""",
        "requirements": """
- Shape is abstract: pure virtual area() and perimeter()
- Both subclasses override area(), perimeter(), print() with override keyword
- Virtual destructor in Shape
- total_area uses Shape** and calls area() polymorphically
- main stores objects as Shape*, demonstrates polymorphic dispatch
""",
        "validation_criteria": """
PASS if:
- Shape has pure virtual methods (= 0)
- Circle and Rectangle correctly override all virtual methods
- Virtual destructor present in Shape
- total_area works via Shape** polymorphically
- main creates and uses shapes via Shape* array

FAIL if:
- Methods not declared virtual
- Missing pure virtual (Shape is not truly abstract)
- No virtual destructor
- total_area doesn't use polymorphism
""",
        "parts": [
            {
                "part_id": "shape_circle",
                "title": "Shape + Circle",
                "language": "cpp",
                "description": (
                    "Implement two C++ classes:\n\n"
                    "1. **`class Shape`** (abstract base class):\n"
                    "   - `virtual double area() const = 0;` — pure virtual\n"
                    "   - `virtual double perimeter() const = 0;` — pure virtual\n"
                    "   - `virtual void print() const;` — prints: `Shape: area=X, perimeter=Y`\n"
                    "   - `virtual ~Shape() {}` — virtual destructor\n\n"
                    "2. **`class Circle : public Shape`**:\n"
                    "   - `double radius;` (private)\n"
                    "   - `Circle(double r)` — constructor\n"
                    "   - `area()` → `M_PI * radius * radius`\n"
                    "   - `perimeter()` → `2 * M_PI * radius`\n"
                    "   - `print()` → prints: `Circle(r=X): area=Y, perimeter=Z`\n\n"
                    "Use `override` keyword. Write only the classes — no `main()`."
                ),
                "setup": _CPP_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}
#define NEAR(a,b) (fabs((double)(a)-(double)(b))<0.01)

int main(){
    Circle c1(5.0);
    CHECK(NEAR(c1.area(), M_PI*25.0),       "Circle(5).area = pi*25");
    CHECK(NEAR(c1.perimeter(), 10.0*M_PI),  "Circle(5).perimeter = 10*pi");

    /* polymorphic dispatch via Shape* */
    Shape* s = new Circle(3.0);
    CHECK(NEAR(s->area(), M_PI*9.0),        "Shape*->Circle(3).area = pi*9");
    CHECK(NEAR(s->perimeter(), 6.0*M_PI),   "Shape*->Circle(3).perimeter = 6*pi");
    delete s;

    Circle c0(0.0);
    CHECK(NEAR(c0.area(), 0.0),             "Circle(0).area = 0");
    CHECK(NEAR(c0.perimeter(), 0.0),        "Circle(0).perimeter = 0");

    Circle c2(1.0);
    CHECK(NEAR(c2.area(), M_PI),            "Circle(1).area = pi");

    if(_ok) std::cout << "ALL_PASS" << std::endl;
    return _ok ? 0 : 1;
}
""",
            },
            {
                "part_id": "rectangle",
                "title": "Rectangle",
                "language": "cpp",
                "description": (
                    "The `Shape` abstract class is already defined for you (do **not** redefine it).\n\n"
                    "Implement **`class Rectangle : public Shape`**:\n"
                    "- `double width, height;` (private)\n"
                    "- `Rectangle(double w, double h)` — constructor\n"
                    "- `area()` → `width * height`\n"
                    "- `perimeter()` → `2 * (width + height)`\n"
                    "- `print()` → prints: `Rectangle(WxH): area=Y, perimeter=Z`\n\n"
                    "Use the `override` keyword. Write only the Rectangle class — no `main()`."
                ),
                "setup": _SHAPE_REF,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}
#define NEAR(a,b) (fabs((double)(a)-(double)(b))<0.01)

int main(){
    Rectangle r1(4.0, 3.0);
    CHECK(NEAR(r1.area(), 12.0),     "Rectangle(4,3).area = 12");
    CHECK(NEAR(r1.perimeter(), 14.0),"Rectangle(4,3).perimeter = 14");

    /* polymorphic via Shape* */
    Shape* s = new Rectangle(5.0, 2.0);
    CHECK(NEAR(s->area(), 10.0),     "Shape*->Rect(5,2).area = 10");
    CHECK(NEAR(s->perimeter(), 14.0),"Shape*->Rect(5,2).perimeter = 14");
    delete s;

    Rectangle sq(3.0, 3.0);
    CHECK(NEAR(sq.area(), 9.0),      "Rectangle(3,3).area = 9");
    CHECK(NEAR(sq.perimeter(), 12.0),"Rectangle(3,3).perimeter = 12");

    Rectangle thin(10.0, 0.5);
    CHECK(NEAR(thin.area(), 5.0),    "Rectangle(10,0.5).area = 5");

    if(_ok) std::cout << "ALL_PASS" << std::endl;
    return _ok ? 0 : 1;
}
""",
            },
            {
                "part_id": "total_area",
                "title": "total_area",
                "language": "cpp",
                "description": (
                    "`Shape`, `Circle`, and `Rectangle` are already defined for you.\n\n"
                    "Implement:\n\n"
                    "`double total_area(Shape** shapes, int n)` — iterate over the array of `n` Shape pointers "
                    "and return the **sum of all areas** using polymorphic dispatch (`shapes[i]->area()`).\n\n"
                    "Write only this function — no `main()`."
                ),
                "setup": _SHAPE_CIRCLE_RECT_REF,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}
#define NEAR(a,b) (fabs((double)(a)-(double)(b))<0.01)

int main(){
    Shape* shapes[3] = {
        new Circle(2.0),
        new Rectangle(3.0, 4.0),
        new Circle(1.0)
    };
    double expected = M_PI*4.0 + 12.0 + M_PI;
    CHECK(NEAR(total_area(shapes, 3), expected), "total of Circle(2)+Rect(3,4)+Circle(1)");
    CHECK(NEAR(total_area(shapes, 0), 0.0),      "total_area of 0 shapes = 0");
    CHECK(NEAR(total_area(shapes, 1), M_PI*4.0), "total_area of 1 shape = Circle(2).area");
    for(int i=0;i<3;i++) delete shapes[i];

    if(_ok) std::cout << "ALL_PASS" << std::endl;
    return _ok ? 0 : 1;
}
""",
            },
        ],
    },

    {
        "id": "cpp_operator_overload",
        "name": "C++ Operator Overloading — Complex Numbers",
        # NOTE: unlike accumulate_code (which concatenates separate free
        # functions from each part — see strings_no_lib/linked_list), this
        # scenario's parts each need the *entire* Complex class re-declared
        # (a C++ class can't be split across two `class Complex {...};`
        # blocks by simple concatenation — that's a duplicate-definition
        # error). carry_forward_code instead pre-fills the next part's editor
        # with the code the student just passed, so they extend one growing
        # class definition in place instead of retyping it from memory.
        "carry_forward_code": True,
        "dev_requirement": """**Task: Complex Number Class with Operator Overloading**

```cpp
class Complex {
    double real, imag;
public:
    Complex(double r = 0, double i = 0);

    Complex operator+(const Complex& o) const;
    Complex operator-(const Complex& o) const;
    Complex operator*(const Complex& o) const;  // (a+bi)(c+di) = (ac-bd) + (ad+bc)i
    bool   operator==(const Complex& o) const;
    Complex& operator+=(const Complex& o);
    Complex operator-() const;                  // unary negation
    double abs() const;                         // sqrt(real*real + imag*imag)

    friend std::ostream& operator<<(std::ostream& os, const Complex& c);
    // Format: "3+4i", "3-4i", "5+0i" — never print "3+-4i"
};
```

Write `main()` that:
- Tests all operators
- Computes `(3+4i) * (1-2i)` and prints the result
- Demonstrates `operator<<` via cout
- Tests `operator==` with equal and unequal pairs""",
        "requirements": """
- operator* uses the correct formula: real=(ac-bd), imag=(ad+bc)
- operator<< handles negative imaginary part correctly (no "3+-4i")
- operator+= modifies *this and returns *this by reference
- abs() uses sqrt(real*real + imag*imag)
- operator== compares both real and imag
""",
        "validation_criteria": """
PASS if:
- operator* uses correct complex multiplication
- operator<< prints correct format for all sign combinations
- operator+= modifies and returns *this
- abs() computed correctly with sqrt
- main tests all operators including (3+4i)*(1-2i)

FAIL if:
- operator* just multiplies real and imag independently
- operator<< shows "3+-4i" for negative imaginary
- operator+= doesn't return *this by reference
""",
        "parts": [
            {
                "part_id": "complex_basic",
                "title": "Complex class — +, -, ==, abs()",
                "language": "cpp",
                "description": (
                    "Implement the `Complex` class with these members:\n\n"
                    "- `double real, imag;` (private)\n"
                    "- `Complex(double r = 0, double i = 0)` — constructor\n"
                    "- `Complex operator+(const Complex& o) const` — adds real and imag parts\n"
                    "- `Complex operator-(const Complex& o) const` — subtracts real and imag parts\n"
                    "- `bool operator==(const Complex& o) const` — true if both real and imag are equal\n"
                    "- `double abs() const` — returns `sqrt(real*real + imag*imag)`\n\n"
                    "Write only the class — no `main()`."
                ),
                "setup": _CPP_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}
#define NEAR(a,b) (fabs((double)(a)-(double)(b))<0.001)

int main(){
    Complex a(3, 4), b(1, -2), zero;

    Complex s = a + b;  /* (3+1)+(4-2)i = 4+2i */
    CHECK(NEAR(s.abs(), sqrt(16.0+4.0)), "(3+4i)+(1-2i)=4+2i, abs should be sqrt(20)");

    Complex add = Complex(1,2) + Complex(3,4);
    CHECK(NEAR(add.abs(), sqrt(16.0+36.0)), "(1+2i)+(3+4i)=4+6i, abs should be sqrt(52)");

    Complex sub = a - b;  /* (3-1)+(4-(-2)) = 2+6i */
    CHECK(NEAR(sub.abs(), sqrt(4.0+36.0)), "(3+4i)-(1-2i)=2+6i");

    CHECK(a == Complex(3,4),   "3+4i == 3+4i");
    CHECK(!(a == b),           "3+4i != 1-2i");
    CHECK(zero == Complex(0,0),"0 == 0");

    CHECK(NEAR(a.abs(), 5.0),         "abs(3+4i)=5");
    CHECK(NEAR(b.abs(), sqrt(5.0)),   "abs(1-2i)=sqrt(5)");
    CHECK(NEAR(zero.abs(), 0.0),      "abs(0)=0");

    if(_ok) std::cout << "ALL_PASS" << std::endl;
    return _ok ? 0 : 1;
}
""",
            },
            {
                "part_id": "complex_advanced",
                "title": "Complex — *, +=, unary -",
                "language": "cpp",
                "description": (
                    "**Your `Complex` class from the previous part is already loaded in the editor** — extend it in place, don't retype it.\n\n"
                    "Add these operators:\n\n"
                    "- `Complex operator*(const Complex& o) const` — complex multiplication:\n"
                    "  `(a+bi)(c+di) = (ac−bd) + (ad+bc)i`\n\n"
                    "- `Complex& operator+=(const Complex& o)` — add `o` to `*this` in-place; **return `*this` by reference**.\n\n"
                    "- `Complex operator-() const` — unary negation: returns `Complex(-real, -imag)`.\n\n"
                    "Keep `+`, `-`, `==`, `abs()` from the previous part — they're still there in the editor. Write the full class — no `main()`."
                ),
                "setup": _CPP_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}
#define NEAR(a,b) (fabs((double)(a)-(double)(b))<0.001)

int main(){
    Complex a(3, 4), b(1, -2);

    /* (3+4i)*(1-2i) = (3*1-4*(-2)) + (3*(-2)+4*1)i = 11 - 2i */
    Complex mul = a * b;
    CHECK(NEAR(mul.abs(), sqrt(121.0+4.0)), "(3+4i)*(1-2i) abs = sqrt(125)");

    Complex i(0, 1);
    Complex i2 = i * i;  /* i*i = -1 */
    CHECK(NEAR(i2.abs(), 1.0), "i*i = -1, abs=1");

    /* += */
    Complex c(1, 1);
    Complex& ref = (c += Complex(2, 3));
    CHECK(c == Complex(3, 4),  "1+1i += 2+3i = 3+4i");
    CHECK(&ref == &c,          "+= returns *this by reference");

    /* unary - */
    Complex neg = -a;
    CHECK(neg == Complex(-3, -4), "-(3+4i) = -3-4i");
    Complex neg0 = -Complex(0,0);
    CHECK(neg0 == Complex(0,0),   "-(0) = 0");

    if(_ok) std::cout << "ALL_PASS" << std::endl;
    return _ok ? 0 : 1;
}
""",
            },
            {
                "part_id": "complex_stream",
                "title": "Complex — operator<<",
                "language": "cpp",
                "description": (
                    "**Your `Complex` class from the previous part is already loaded in the editor** — extend it one final time, don't retype it.\n\n"
                    "Add:\n\n"
                    "`friend std::ostream& operator<<(std::ostream& os, const Complex& c)`\n\n"
                    "**Format rules:**\n"
                    "- Positive imaginary: `3+4i`\n"
                    "- Negative imaginary: `3-4i` ← **NOT** `3+-4i`\n"
                    "- Zero imaginary: `3+0i` or `3-0i` (either is fine)\n"
                    "- Zero real, positive imag: `0+4i`\n\n"
                    "The key requirement: when `imag < 0`, print the `-` sign once, not `+-`.\n\n"
                    "Write the full class — no `main()`."
                ),
                "setup": _CPP_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}

static std::string fmt(const Complex& c){
    std::ostringstream oss; oss << c; return oss.str();
}

int main(){
    CHECK(fmt(Complex(3,4))  == "3+4i",  "3+4i format");
    CHECK(fmt(Complex(3,-4)) == "3-4i",  "3-4i (not 3+-4i)");
    CHECK(fmt(Complex(0,0))  == "0+0i" || fmt(Complex(0,0)) == "0-0i", "0+0i");

    /* must NOT contain "+-" */
    std::string s = fmt(Complex(5, -2));
    CHECK(s.find("+-") == std::string::npos, "no '+-' in output for 5-2i");
    CHECK(s.find("5")  != std::string::npos, "output contains 5");
    CHECK(s.find("2")  != std::string::npos, "output contains 2");

    CHECK(fmt(Complex(1,1))  == "1+1i",  "1+1i");
    CHECK(fmt(Complex(-1,2)) == "-1+2i", "-1+2i");

    if(_ok) std::cout << "ALL_PASS" << std::endl;
    return _ok ? 0 : 1;
}
""",
            },
        ],
    },

    {
        "id": "cpp_template",
        "name": "C++ Generic Templates",
        "dev_requirement": """**Task: Generic C++ Templates — Pair and Stack**

**Part 1: Pair<T, U>**
```cpp
template<typename T, typename U>
class Pair {
    T first;
    U second;
public:
    Pair(T f, U s);
    T getFirst() const;
    U getSecond() const;
    void print() const;   // prints "(first, second)"
};
```

**Part 2: Stack<T>** — generic stack with a growing array (use `new`/`delete`, not malloc)
```cpp
template<typename T>
class Stack {
    T* data;
    int top_idx;
    int capacity;
    void grow();   // double capacity: new T[capacity*2], copy, delete[] old
public:
    Stack(int initial_capacity = 4);
    ~Stack();
    void push(const T& val);
    T pop();    // throw std::underflow_error if empty
    T& peek();  // throw std::underflow_error if empty
    bool empty() const;
    int size() const;
};
```

Write `main()` demonstrating:
- `Pair<int, std::string>` and `Pair<double, double>`
- `Stack<int>` — push several values, peek, pop all
- `Stack<std::string>` — push strings, pop and print""",
        "requirements": """
- Pair: two separate template type parameters T and U
- Stack: dynamic array with new/delete (not malloc)
- grow(): allocate new T[capacity*2], copy old elements, delete[] old array
- push() calls grow() when top_idx == capacity
- pop() and peek() throw std::underflow_error on empty stack
- ~Stack() calls delete[] data
- main demonstrates both Pair types and both Stack types
""",
        "validation_criteria": """
PASS if:
- Pair correctly parameterized with two independent types
- Stack uses dynamic new/delete array
- grow() doubles capacity and copies all elements
- pop/peek throw std::underflow_error on empty stack
- Destructor calls delete[] data
- main demonstrates Pair<int,string>, Pair<double,double>, Stack<int>, Stack<string>

FAIL if:
- Uses malloc/realloc instead of new/delete
- grow() doesn't copy existing elements
- No exception thrown on pop/peek from empty stack
- Missing destructor or memory leak
""",
        "parts": [
            {
                "part_id": "pair_template",
                "title": "Pair<T, U>",
                "language": "cpp",
                "description": (
                    "Implement a generic `Pair<T, U>` class template with **two independent type parameters**:\n\n"
                    "```cpp\n"
                    "template<typename T, typename U>\n"
                    "class Pair {\n"
                    "    T first;\n"
                    "    U second;\n"
                    "public:\n"
                    "    Pair(T f, U s);\n"
                    "    T getFirst() const;\n"
                    "    U getSecond() const;\n"
                    "    void print() const;  // prints: (first, second)\n"
                    "};\n"
                    "```\n\n"
                    "Write only the class template — no `main()`."
                ),
                "setup": _CPP_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}
#define NEAR(a,b) (fabs((double)(a)-(double)(b))<0.001)

int main(){
    Pair<int, std::string> p1(42, "hello");
    CHECK(p1.getFirst() == 42,        "Pair<int,str>.first = 42");
    CHECK(p1.getSecond() == "hello",  "Pair<int,str>.second = hello");

    Pair<double, double> p2(3.14, 2.71);
    CHECK(NEAR(p2.getFirst(), 3.14),  "Pair<double,double>.first = 3.14");
    CHECK(NEAR(p2.getSecond(), 2.71), "Pair<double,double>.second = 2.71");

    Pair<std::string, int> p3("world", 99);
    CHECK(p3.getFirst() == "world",   "Pair<str,int>.first = world");
    CHECK(p3.getSecond() == 99,       "Pair<str,int>.second = 99");

    Pair<bool, char> p4(true, 'X');
    CHECK(p4.getFirst() == true,      "Pair<bool,char>.first = true");
    CHECK(p4.getSecond() == 'X',      "Pair<bool,char>.second = X");

    if(_ok) std::cout << "ALL_PASS" << std::endl;
    return _ok ? 0 : 1;
}
""",
            },
            {
                "part_id": "stack_template",
                "title": "Stack<T>",
                "language": "cpp",
                "description": (
                    "Implement a generic `Stack<T>` class template backed by a **dynamic array** (`new`/`delete` — **not** `malloc`).\n\n"
                    "```cpp\n"
                    "template<typename T>\n"
                    "class Stack {\n"
                    "    T* data;\n"
                    "    int top_idx;   // index of next free slot (-1 when empty? or 0-based size?)\n"
                    "    int capacity;\n"
                    "    void grow();   // double capacity, copy, delete[] old\n"
                    "public:\n"
                    "    Stack(int initial_capacity = 4);\n"
                    "    ~Stack();                // delete[] data\n"
                    "    void push(const T& val); // grow() if full\n"
                    "    T    pop();              // throw std::underflow_error if empty\n"
                    "    T&   peek();             // throw std::underflow_error if empty\n"
                    "    bool empty() const;\n"
                    "    int  size() const;\n"
                    "};\n"
                    "```\n\n"
                    "Write only the class template — no `main()`."
                ),
                "setup": _CPP_BASE,
                "test_harness": r"""
static int _ok = 1;
#define CHECK(c,m) if(!(c)){std::cerr<<"FAIL: "<<m<<"\n";_ok=0;}

int main(){
    Stack<int> s;
    CHECK(s.empty(),     "new Stack is empty");
    CHECK(s.size() == 0, "new Stack size = 0");

    s.push(10); s.push(20); s.push(30);
    CHECK(!s.empty(),    "not empty after 3 pushes");
    CHECK(s.size() == 3, "size = 3");
    CHECK(s.peek() == 30,"peek = 30 (top)");
    CHECK(s.pop() == 30, "pop = 30");
    CHECK(s.pop() == 20, "pop = 20");
    CHECK(s.pop() == 10, "pop = 10");
    CHECK(s.empty(),     "empty after all pops");

    /* grow past initial capacity (default 4) */
    Stack<int> big;
    for(int i = 0; i < 10; i++) big.push(i);
    CHECK(big.size() == 10, "size = 10 after grow");
    CHECK(big.peek() == 9,  "peek = 9 after grow");

    /* exception on empty pop */
    Stack<int> mt;
    bool threw = false;
    try { mt.pop(); } catch(std::underflow_error&) { threw = true; }
    CHECK(threw, "pop() throws underflow_error on empty");

    bool threw2 = false;
    try { mt.peek(); } catch(std::underflow_error&) { threw2 = true; }
    CHECK(threw2, "peek() throws underflow_error on empty");

    /* Stack<string> */
    Stack<std::string> ss;
    ss.push("hello"); ss.push("world");
    CHECK(ss.pop() == "world", "Stack<string> pop = world");
    CHECK(ss.pop() == "hello", "Stack<string> pop = hello");

    if(_ok) std::cout << "ALL_PASS" << std::endl;
    return _ok ? 0 : 1;
}
""",
            },
        ],
    },

    {
        "id": "cpp_stl",
        "name": "C++ STL — Word Frequency Counter",
        "dev_requirement": """**Task: Word Frequency Counter Using C++ STL**

Write a C++ program that:

1. Takes an input filename as `argv[1]`
2. Reads words using `std::ifstream` + `>>` operator
3. Converts each word to **lowercase** using `std::transform` + `::tolower`
4. Counts frequency in `std::map<std::string, int>`
5. Copies map entries into `std::vector<std::pair<int,std::string>>` and sorts descending by count using `std::sort` with a lambda
6. Prints:
```
Total unique words: 42
Top 5 words:
  the: 15
  and: 12
  ...
```
7. Implement `std::string to_lower(std::string s)` as a helper function.

Error handling: if argc < 2 or file not opened, print error and exit(1).""",
        "requirements": """
- std::ifstream for file reading
- std::map<string,int> for frequency counting
- to_lower uses std::transform with ::tolower
- std::vector<pair<int,string>> for sorting by frequency
- std::sort with lambda: [](auto& a, auto& b){ return a.first > b.first; }
- Prints top 5 (or fewer if less than 5 unique words)
- Error handling for argc and fopen
""",
        "validation_criteria": """
PASS if:
- std::map correctly counts word frequencies
- Words converted to lowercase before counting
- std::sort with custom lambda for descending frequency
- to_lower correctly uses std::transform
- Top-5 printed correctly
- Error handled for missing argument or bad file

FAIL if:
- Case-sensitive counting (no tolower)
- Manual sort instead of std::sort
- Uses C arrays instead of STL containers
- No error handling
""",
    },

    {
        "id": "cpp_smart_ptrs",
        "name": "C++ Smart Pointers",
        "dev_requirement": """**Task: Smart Pointers — unique_ptr and shared_ptr**

**Part 1: unique_ptr linked list**

Define a Node struct using `unique_ptr` for `next` — **no raw pointers**:
```cpp
struct Node {
    int val;
    std::unique_ptr<Node> next;
    Node(int v) : val(v), next(nullptr) {}
};
```
Build a linked list of 3 nodes using `std::make_unique<Node>()`. Traverse and print the list. Notice: **no `delete` needed**.

**Part 2: shared_ptr reference counting**

Define:
```cpp
struct Resource {
    std::string name;
    Resource(const std::string& n) : name(n) {}
    ~Resource() { std::cout << "Resource " << name << " destroyed\\n"; }
};
```
- Create `std::shared_ptr<Resource> a = std::make_shared<Resource>("DB");`
- Create `b` and `c` as copies of `a`
- After each copy, print `use_count()`
- Let `a`, `b`, `c` go out of scope (use blocks `{}`) and observe when the destructor fires

**Part 3:** Add a comment block explaining:
- Why `unique_ptr` **cannot be copied** (deleted copy constructor)
- How to transfer ownership using `std::move`""",
        "requirements": """
- Part 1: Node uses unique_ptr<Node> next, no raw new/delete
- List built with make_unique, traversal works
- Part 2: use_count() printed after each assignment and after each scope exit
- Destructor message appears only when last shared_ptr is released
- Part 3: comment explains single ownership and std::move
""",
        "validation_criteria": """
PASS if:
- Node uses std::unique_ptr<Node> next (no raw pointers)
- List of 3 nodes built with make_unique, no explicit delete
- shared_ptr use_count() correctly demonstrates reference counting
- Resource destructor fires when last shared_ptr goes out of scope
- Comment correctly explains unique_ptr's move-only ownership model

FAIL if:
- Raw pointers used instead of smart pointers
- use_count() not demonstrated
- Resource destroyed prematurely or not at all
- Missing comment on move semantics
""",
    },
]


class ScenarioManager:
    def __init__(self):
        self.scenarios = SCENARIOS

    def get_scenario(self, student_id: str = "gen_user", exclude_ids: list = None) -> Dict[str, Any]:
        exclude_ids = exclude_ids or []
        available = [s for s in self.scenarios if s["id"] not in exclude_ids]
        if not available:
            available = self.scenarios  # student completed all — cycle again
        seed = sum(ord(c) for c in student_id) % (2 ** 32)
        random.seed(seed + len(exclude_ids))
        return random.choice(available)

    def get_all_scenarios(self) -> List[Dict[str, Any]]:
        return self.scenarios
