\
#include <iostream>
#include <string>
#include <vector>

namespace {

struct Args {
  std::vector<std::string> values;
};

void print_usage() {
  std::cerr
    << "Usage:\n"
    << "  forks-core status\n"
    << "  forks-core audit --gadget <gizmo> <gadget>\n";
}

std::string json_escape(const std::string& text) {
  std::string out;
  for (char ch : text) {
    if (ch == '\\') out += "\\\\";
    else if (ch == '"') out += "\\\"";
    else if (ch == '\n') out += "\\n";
    else out += ch;
  }
  return out;
}

void print_status() {
  std::cout
    << "{\n"
    << "  \"format\": \"FORKS_CORE_STATUS_V0\",\n"
    << "  \"command\": \"status\",\n"
    << "  \"mutation_scope\": \"read-only\",\n"
    << "  \"mutates\": false,\n"
    << "  \"implemented\": false,\n"
    << "  \"expected_facts\": [\n"
    << "    \"integration_ref\",\n"
    << "    \"agent_refs\",\n"
    << "    \"ahead_behind\",\n"
    << "    \"replay_ledger_entries\",\n"
    << "    \"expected_mutations\"\n"
    << "  ]\n"
    << "}\n";
}

int audit_gadget(const Args& args) {
  std::string gizmo;
  std::string gadget;
  for (size_t i = 1; i < args.values.size(); ++i) {
    if (args.values[i] == "--gadget" && i + 2 < args.values.size()) {
      gizmo = args.values[i + 1];
      gadget = args.values[i + 2];
      break;
    }
  }
  if (gizmo.empty() || gadget.empty()) {
    std::cerr << "audit requires --gadget <gizmo> <gadget>\n";
    return 1;
  }
  std::cout
    << "{\n"
    << "  \"format\": \"FORKS_CORE_AUDIT_V0\",\n"
    << "  \"command\": \"audit\",\n"
    << "  \"mutation_scope\": \"read-only\",\n"
    << "  \"mutates\": false,\n"
    << "  \"implemented\": false,\n"
    << "  \"gadget\": {\n"
    << "    \"gizmo\": \"" << json_escape(gizmo) << "\",\n"
    << "    \"gadget\": \"" << json_escape(gadget) << "\"\n"
    << "  },\n"
    << "  \"expected_facts\": [\n"
    << "    \"payload_presence\",\n"
    << "    \"latest_writer_per_path\",\n"
    << "    \"strict_mismatches\",\n"
    << "    \"advisory_mismatches\",\n"
    << "    \"materialisation_result\"\n"
    << "  ]\n"
    << "}\n";
  return 0;
}

} // namespace

int main(int argc, char** argv) {
  Args args;
  for (int i = 1; i < argc; ++i) args.values.push_back(argv[i]);
  if (args.values.empty()) {
    print_usage();
    return 1;
  }

  const std::string command = args.values[0];
  if (command == "status") {
    print_status();
    return 0;
  }
  if (command == "audit") {
    return audit_gadget(args);
  }

  std::cerr << "unsupported forks-core command in read-only scaffold: " << command << "\n";
  print_usage();
  return 1;
}
