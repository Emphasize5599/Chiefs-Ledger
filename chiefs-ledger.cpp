#include <iostream>
#include <fstream>
#include <string>
#include <vector>
#include <map>
#include <cmath>

using namespace std;

// CONSTANTS FOR USE IN FUNCTIONS
const string DIGITS = "0123456789abcdef";
const vector<string> arr = {"0", "2", "8", "9", "P", "Y", "L", "Q", "G", "R", "J", "C", "U", "V"};

// CONVERSION INTO BYTE ARRAY
string base10_to_base256(int number) {
    vector<int> base256_values(8, 0);
    int index = 7;
    while (number > 0 && index >= 0) {
        int remainder = number % 256;
        base256_values[index] = remainder;
        number /= 256;
        index--;
    }
    string result;
    for (size_t i = 0; i < base256_values.size(); i++) {
        result += to_string(base256_values[i]);
        if (i < base256_values.size() - 1) result += ", ";
    }
    return result;
}

// GENERATE DATA STRUCTURE FOR BYTE ARRAYS TO BE CONVERTED INTO A LIST OF TAGS
map<int, string> generate_256_values(int start, int end) {
    map<int, string> values_256;
    for (int num = start; num <= end; ++num) {
        values_256[num] = base10_to_base256(num);
    }
    return values_256;
}

// CONVERTS BASE 256 ARRAYS TO BASE 14 ARRAYS
string convert_to_base(int decimal_number, int base) {
    vector<int> remainder_stack;
    while (decimal_number > 0) {
        int remainder = decimal_number % base;
        remainder_stack.push_back(remainder);
        decimal_number /= base;
    }
    string new_digits;
    while (!remainder_stack.empty()) {
        new_digits += DIGITS[remainder_stack.back()];
        remainder_stack.pop_back();
    }
    return new_digits;
}

// CONVERTS BASE 14 ARRAYS INTO TAGS
string decalc(const string &a) {
    vector<int> tz;
    size_t start = 0, end;
    while ((end = a.find(",", start)) != string::npos) {
        tz.push_back(stoi(a.substr(start, end - start)));
        start = end + 1;
    }
    tz.push_back(stoi(a.substr(start)));

    if (tz.size() != 8) return "";

    int low = 0, high = 0;
    for (int i = 0; i < 4; ++i) {
        low = (low + tz[i]) * 0x100;
    }
    low /= 0x100;

    for (int i = 4; i < 8; ++i) {
        high = (high + tz[i]) * 0x100;
    }
    high /= 0x100;

    int total = low + high * 0x100;
    string out = convert_to_base(total, 14);
    for (size_t i = 0; i < out.size(); ++i) {
        out[i] = arr[stoi(string(1, out[i]), nullptr, 16)][0];
    }
    if (out.length() <= 9) {
        return out;
    }
    return "";
}

/*
**************************************** MATH AND LIBRARIES ABOVE, DON'T TOUCH ****************************************
*/

void clear() {
    cout << string(100, '\n');
}

void programinfo() {
    cout << "===Chief's Ledger v0.0.1 alpha===" << endl;
}

// RUNS UPON PROGRAM LAUNCH
void acknowledgementprompt() {
    programinfo();
    cout << "Greetings, Chief! We have been waiting for you." << endl;
    cout << "With this program, you can find the oldest players in the game, and see who is still active." << endl;
    cout << "Use this program to explore, build connections, or simply watch from a distance." << endl << endl;
    cout << "Keep in mind that this program runs on your machine and uses your internet connection," << endl;
    cout << "so adjust the batch size accordingly. Most machines should handle a batch size of 500000 with ease," << endl;
    cout << "but make sure that your internet service provider will tolerate a large amount of DNS requests," << endl;
    cout << "should you choose to monitor a large amount of players." << endl << endl;
    cout << "Press enter to acknowledge that you have read and understood this statement." << endl << endl;
    cin.ignore(); // Ignores any remaining newline character
}

// OUTPUTS TAGS INTO TEXT FILES
void run_decalc_and_capture_output(const map<int, string> &values_dict, const string &output_directory, const string &output_file) {
    ofstream file(output_directory + "/" + output_file);
    for (const auto &pair : values_dict) {
        string result = decalc(pair.second);
        if (!result.empty()) {
            file << result << "\n";
        }
    }
    file.close();
}

// COMBINES TEXT FILES INTO ONE FILE
void combine_files(const string &file_prefix, int batch_count, const string &output_directory, const string &output_file) {
    ofstream outfile(output_directory + "/" + output_file);
    for (int i = 0; i < batch_count; ++i) {
        ifstream infile(output_directory + "/" + file_prefix + to_string(i) + ".txt");
        if (infile) {
            outfile << infile.rdbuf();
            infile.close();
        }
    }
    outfile.close();
}

// PARAMETER DEFINITIONS AND TAG GENERATION
void taggenfile() {
    clear();
    programinfo();
    int start_range, end_range, batch_size;
    string directory;
    cout << "Enter the start of the range (base 10): ";
    cin >> start_range;
    cout << "Enter the end of the range (base 10): ";
    cin >> end_range;
    cout << "Enter the batch size: ";
    cin >> batch_size;
    cout << "Please specify your output directory of choice:" << endl;
    cin >> directory;
    cout << "Got it! Hopefully you don't break my brain! Generating..." << endl << endl;
    
    int batch_count = ceil((end_range - start_range + 1) / static_cast<double>(batch_size));

    for (int i = 0; i < batch_count; ++i) {
        int batch_start = start_range + i * batch_size;
        int batch_end = min(start_range + (i + 1) * batch_size - 1, end_range);
        auto values_256 = generate_256_values(batch_start, batch_end);
        // Save each batch file to the specified directory
        run_decalc_and_capture_output(values_256, directory, "tags" + to_string(i) + ".txt");
    }

    // Combine all batch files into one file in the specified directory
    combine_files("tags", batch_count, directory, "combined_output.txt");

    clear();
    cout << "Successfully exported to: " << directory << endl << endl;
}

int menuchoice = -1;

void mainmenu() {
    while (true) {
        programinfo();
        cout << "Here are the tools at your disposal, Chief. Please select an option to craft your Ledger." << endl << endl;
        cout << "1) Decipher a player tag to its player number." << endl;
        cout << "2) Translate a player number to its player tag." << endl;
        cout << "3) Specify a range of player numbers that you want to translate into tags." << endl;
        cout << "4) Specify a range of player numbers that you want to translate into tags," << endl;
        cout << "   but output the tags to a .txt file in a specified directory." << endl;
        cout << "5) Import a .txt file to construct a player database." << endl;
        cout << "6) Configure a monitoring schedule for your player database." << endl;
        cout << "7) Import a .txt file to construct a clans database." << endl;
        cout << "8) Configure a monitoring schedule for your clans database." << endl;
        cout << "0) Terminate program." << endl << endl;
   
        cin >> menuchoice;

        switch (menuchoice) {
            case 1:
                // ADD FUNCTION
                break;
            case 2:
                // ADD FUNCTION
                break;
            case 3:
                // ADD FUNCTION
                break;
            case 4:
                taggenfile();
                break;
            case 5:
                // ADD FUNCTION
                break;
            case 6:
                // ADD FUNCTION
                break;
            case 7:
                // ADD FUNCTION
                break;
            case 8:
                // ADD FUNCTION
                break;
            case 0:
                cout << "Closing your ledger..." << endl;
                return;
            default:
                // Handle invalid input
                cout << "Chief, we could not understand your input! Please input a valid integer.";
                break;
        }
    }
}



int main() {
    acknowledgementprompt();

    mainmenu();

    return 0;
}
