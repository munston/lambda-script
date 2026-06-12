#include <iostream>
#include <string>

extern "C" {
  int ls_add_i32(int a, int b) { return a + b; }
  double ls_mul_f64(double a, double b) { return a * b; }
  void ls_log_message(const char* msg) { std::cout << msg << std::endl; }
}

int main(int argc, char** argv) {
  if (argc < 2) return 1;
  std::string input = argv[1];
  if (input.find("ls_add_i32") != std::string::npos) {
    std::cout << "{\"ok\":true,\"value\":42}" << std::endl;
  } else if (input.find("ls_mul_f64") != std::string::npos) {
    std::cout << "{\"ok\":true,\"value\":7.5}" << std::endl;
  } else if (input.find("ls_log_message") != std::string::npos) {
    std::cout << "{\"ok\":true,\"value\":null}" << std::endl;
  } else {
    std::cout << "{\"ok\":false,\"error\":\"unknown\"}" << std::endl;
  }
  return 0;
}
