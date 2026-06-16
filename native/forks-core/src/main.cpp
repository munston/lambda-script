#include <array>
#include <cstdio>
#include <cstdlib>
#include <iostream>
#include <sstream>
#include <string>
#include <vector>

#ifdef _WIN32
#define FORKS_POPEN _popen
#define FORKS_PCLOSE _pclose
#else
#define FORKS_POPEN popen
#define FORKS_PCLOSE pclose
#endif

namespace {

struct Args {
  std::vector<std::string> values;
};

struct SubprocessResult {
  int status = 1;
  std::string stdout_text;
};

struct GadgetTarget {
  std::string gizmo;
  std::string gadget;
  std::string integration_ref;
  std::string agent_branch_template;
};

struct RefProbe {
  std::string ref;
  bool exists = false;
  std::string head;
  std::string error;
};

struct AgentLane {
  std::string agent;
  std::string ref;
  bool exists = false;
  std::string head;
  std::string relation;
  int ahead = 0;
  int behind = 0;
  std::string error;
};

struct ExpectedMutation {
  std::string scope;
  std::string ref;
  std::string mode;
};

struct CommandPlan {
  std::string command;
  std::string mutation_scope;
  bool mutates;
  GadgetTarget gadget;
  RefProbe integration;
  std::vector<AgentLane> lanes;
  std::vector<ExpectedMutation> expected_mutations;
};

const std::vector<std::string> kDefaultAgents = {"ed", "edd", "eddy", "guy"};

void print_usage() {
  std::cerr
    << "Usage:\n"
    << "  forks-core status [--gadget <gizmo> <gadget>]\n"
    << "  forks-core audit --gadget <gizmo> <gadget>\n";
}

std::string trim(std::string text) {
  while (!text.empty() && (text.back() == '\n' || text.back() == '\r' || text.back() == ' ' || text.back() == '\t')) text.pop_back();
  size_t start = 0;
  while (start < text.size() && (text[start] == ' ' || text[start] == '\t' || text[start] == '\n' || text[start] == '\r')) start++;
  return text.substr(start);
}

bool is_safe_name(const std::string& text) {
  if (text.empty()) return false;
  for (char ch : text) {
    const bool ok = (ch >= 'A' && ch <= 'Z') || (ch >= 'a' && ch <= 'z') || (ch >= '0' && ch <= '9') || ch == '_' || ch == '-';
    if (!ok) return false;
  }
  return true;
}

std::string json_escape(const std::string& text) {
  std::string out;
  for (char ch : text) {
    if (ch == '\\') out += "\\\\";
    else if (ch == '"') out += "\\\"";
    else if (ch == '\n') out += "\\n";
    else if (ch == '\r') out += "\\r";
    else if (ch == '\t') out += "\\t";
    else out += ch;
  }
  return out;
}

std::string json_string(const std::string& text) {
  return "\"" + json_escape(text) + "\"";
}

SubprocessResult run_readonly_command(const std::string& command) {
  SubprocessResult result;
  std::array<char, 256> buffer{};
  FILE* pipe = FORKS_POPEN(command.c_str(), "r");
  if (!pipe) {
    result.status = 1;
    return result;
  }
  while (fgets(buffer.data(), static_cast<int>(buffer.size()), pipe) != nullptr) {
    result.stdout_text += buffer.data();
  }
  result.status = FORKS_PCLOSE(pipe);
  result.stdout_text = trim(result.stdout_text);
  return result;
}

GadgetTarget make_gadget_target(const std::string& gizmo, const std::string& gadget) {
  GadgetTarget target;
  target.gizmo = gizmo;
  target.gadget = gadget;
  target.integration_ref = "origin/gadgets/" + gizmo + "/" + gadget + "/main";
  target.agent_branch_template = "origin/gadget-agents/" + gizmo + "/" + gadget + "/{agent}";
  return target;
}

std::string agent_ref(const GadgetTarget& target, const std::string& agent) {
  return "origin/gadget-agents/" + target.gizmo + "/" + target.gadget + "/" + agent;
}

RefProbe probe_ref(const std::string& ref) {
  RefProbe probe;
  probe.ref = ref;
  const SubprocessResult result = run_readonly_command("git rev-parse --verify --quiet " + ref);
  if (result.status == 0 && !result.stdout_text.empty()) {
    probe.exists = true;
    probe.head = result.stdout_text;
  } else {
    probe.exists = false;
    probe.error = "ref not found";
  }
  return probe;
}

bool parse_two_counts(const std::string& text, int& left, int& right) {
  std::istringstream in(text);
  in >> left >> right;
  return !in.fail();
}

AgentLane inspect_agent_lane(const GadgetTarget& target, const RefProbe& integration, const std::string& agent) {
  AgentLane lane;
  lane.agent = agent;
  lane.ref = agent_ref(target, agent);
  const RefProbe lane_ref = probe_ref(lane.ref);
  lane.exists = lane_ref.exists;
  lane.head = lane_ref.head;
  if (!lane.exists) {
    lane.relation = "missing";
    lane.error = lane_ref.error;
    return lane;
  }
  if (!integration.exists) {
    lane.relation = "unknown";
    lane.error = "integration ref missing";
    return lane;
  }
  const SubprocessResult counts = run_readonly_command("git rev-list --left-right --count " + integration.ref + "..." + lane.ref);
  int behind = 0;
  int ahead = 0;
  if (counts.status != 0 || !parse_two_counts(counts.stdout_text, behind, ahead)) {
    lane.relation = "unknown";
    lane.error = "ahead/behind inspection failed";
    return lane;
  }
  lane.behind = behind;
  lane.ahead = ahead;
  if (ahead == 0 && behind == 0) lane.relation = "aligned";
  else if (ahead > 0 && behind == 0) lane.relation = "ahead-only";
  else if (ahead == 0 && behind > 0) lane.relation = "behind-only";
  else lane.relation = "diverged";
  return lane;
}

bool parse_gadget_args(const Args& args, size_t start, GadgetTarget& target, std::string& error) {
  for (size_t i = start; i < args.values.size(); ++i) {
    if (args.values[i] == "--gadget" && i + 2 < args.values.size()) {
      const std::string gizmo = args.values[i + 1];
      const std::string gadget = args.values[i + 2];
      if (!is_safe_name(gizmo) || !is_safe_name(gadget)) {
        error = "gadget names must contain only letters, digits, underscore, or hyphen";
        return false;
      }
      target = make_gadget_target(gizmo, gadget);
      return true;
    }
  }
  error = "missing --gadget <gizmo> <gadget>";
  return false;
}

CommandPlan build_readonly_plan(const std::string& command, const GadgetTarget& target) {
  CommandPlan plan;
  plan.command = command;
  plan.mutation_scope = "read-only";
  plan.mutates = false;
  plan.gadget = target;
  plan.integration = probe_ref(target.integration_ref);
  for (const std::string& agent : kDefaultAgents) {
    plan.lanes.push_back(inspect_agent_lane(target, plan.integration, agent));
  }
  return plan;
}

void print_expected_mutations_empty() {
  std::cout << "  \"expected_mutations\": []\n";
}

void print_gadget(const GadgetTarget& target) {
  std::cout
    << "  \"gadget\": {\n"
    << "    \"gizmo\": " << json_string(target.gizmo) << ",\n"
    << "    \"gadget\": " << json_string(target.gadget) << ",\n"
    << "    \"integration_ref\": " << json_string(target.integration_ref) << ",\n"
    << "    \"agent_branch_template\": " << json_string(target.agent_branch_template) << "\n"
    << "  }";
}

void print_ref_probe(const std::string& key, const RefProbe& ref, bool trailing_comma) {
  std::cout
    << "  \"" << key << "\": {\n"
    << "    \"ref\": " << json_string(ref.ref) << ",\n"
    << "    \"exists\": " << (ref.exists ? "true" : "false") << ",\n"
    << "    \"head\": " << json_string(ref.head) << ",\n"
    << "    \"error\": " << json_string(ref.error) << "\n"
    << "  }" << (trailing_comma ? "," : "") << "\n";
}

void print_lanes(const std::vector<AgentLane>& lanes) {
  std::cout << "  \"agent_lanes\": [\n";
  for (size_t i = 0; i < lanes.size(); ++i) {
    const AgentLane& lane = lanes[i];
    std::cout
      << "    {\n"
      << "      \"agent\": " << json_string(lane.agent) << ",\n"
      << "      \"ref\": " << json_string(lane.ref) << ",\n"
      << "      \"exists\": " << (lane.exists ? "true" : "false") << ",\n"
      << "      \"head\": " << json_string(lane.head) << ",\n"
      << "      \"relation\": " << json_string(lane.relation) << ",\n"
      << "      \"ahead\": " << lane.ahead << ",\n"
      << "      \"behind\": " << lane.behind << ",\n"
      << "      \"error\": " << json_string(lane.error) << "\n"
      << "    }" << (i + 1 < lanes.size() ? "," : "") << "\n";
  }
  std::cout << "  ],\n";
}

void print_plan_json(const std::string& format, const CommandPlan& plan, const std::vector<std::string>& facts) {
  std::cout
    << "{\n"
    << "  \"format\": " << json_string(format) << ",\n"
    << "  \"command\": " << json_string(plan.command) << ",\n"
    << "  \"mutation_scope\": " << json_string(plan.mutation_scope) << ",\n"
    << "  \"mutates\": " << (plan.mutates ? "true" : "false") << ",\n";
  print_gadget(plan.gadget);
  std::cout << ",\n";
  print_ref_probe("integration", plan.integration, true);
  print_lanes(plan.lanes);
  std::cout << "  \"facts\": [\n";
  for (size_t i = 0; i < facts.size(); ++i) {
    std::cout << "    " << json_string(facts[i]) << (i + 1 < facts.size() ? "," : "") << "\n";
  }
  std::cout << "  ],\n";
  print_expected_mutations_empty();
  std::cout << "}\n";
}

int status_command(const Args& args) {
  GadgetTarget target;
  std::string error;
  if (!parse_gadget_args(args, 1, target, error)) {
    std::cout
      << "{\n"
      << "  \"format\": \"FORKS_CORE_STATUS_V2\",\n"
      << "  \"command\": \"status\",\n"
      << "  \"mutation_scope\": \"read-only\",\n"
      << "  \"mutates\": false,\n"
      << "  \"implemented\": true,\n"
      << "  \"requires_gadget_for_ref_inspection\": true,\n"
      << "  \"expected_mutations\": []\n"
      << "}\n";
    return 0;
  }
  const CommandPlan plan = build_readonly_plan("status", target);
  print_plan_json("FORKS_CORE_STATUS_V2", plan, {
    "integration_ref",
    "agent_refs",
    "ahead_behind",
    "expected_mutations"
  });
  return 0;
}

int audit_command(const Args& args) {
  GadgetTarget target;
  std::string error;
  if (!parse_gadget_args(args, 1, target, error)) {
    std::cerr << "audit requires --gadget <gizmo> <gadget>\n";
    return 1;
  }
  const CommandPlan plan = build_readonly_plan("audit", target);
  print_plan_json("FORKS_CORE_AUDIT_V2", plan, {
    "integration_ref",
    "agent_refs",
    "ahead_behind",
    "payload_presence_pending",
    "latest_writer_per_path_pending",
    "materialisation_result_pending"
  });
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
  if (command == "status") return status_command(args);
  if (command == "audit") return audit_command(args);

  std::cerr << "unsupported forks-core command in read-only scaffold: " << command << "\n";
  print_usage();
  return 1;
}
