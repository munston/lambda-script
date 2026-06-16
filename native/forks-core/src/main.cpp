#include <iostream>
#include <string>
#include <vector>

namespace {

struct Args {
  std::vector<std::string> values;
};

struct GadgetTarget {
  std::string gizmo;
  std::string gadget;
  std::string integration_ref;
  std::string agent_branch_template;
};

struct AgentLane {
  std::string agent;
  std::string ref;
  std::string relation;
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
  std::vector<AgentLane> lanes;
  std::vector<ExpectedMutation> expected_mutations;
};

void print_usage() {
  std::cerr
    << "Usage:\n"
    << "  forks-core status [--gadget <gizmo> <gadget>]\n"
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

std::string gadget_integration_ref(const std::string& gizmo, const std::string& gadget) {
  return "origin/gadgets/" + gizmo + "/" + gadget + "/main";
}

std::string gadget_agent_template(const std::string& gizmo, const std::string& gadget) {
  return "origin/gadget-agents/" + gizmo + "/" + gadget + "/{agent}";
}

GadgetTarget make_gadget_target(const std::string& gizmo, const std::string& gadget) {
  return GadgetTarget{gizmo, gadget, gadget_integration_ref(gizmo, gadget), gadget_agent_template(gizmo, gadget)};
}

void print_json_string_field(const std::string& name, const std::string& value, const std::string& indent, bool comma) {
  std::cout << indent << "\"" << name << "\": \"" << json_escape(value) << "\"";
  if (comma) std::cout << ",";
  std::cout << "\n";
}

void print_gadget(const GadgetTarget& gadget, const std::string& indent, bool comma) {
  std::cout << indent << "\"gadget\": {\n";
  print_json_string_field("gizmo", gadget.gizmo, indent + "  ", true);
  print_json_string_field("gadget", gadget.gadget, indent + "  ", true);
  print_json_string_field("integration_ref", gadget.integration_ref, indent + "  ", true);
  print_json_string_field("agent_branch_template", gadget.agent_branch_template, indent + "  ", false);
  std::cout << indent << "}";
  if (comma) std::cout << ",";
  std::cout << "\n";
}

void print_expected_mutations(const std::vector<ExpectedMutation>& mutations, const std::string& indent, bool comma) {
  std::cout << indent << "\"expected_mutations\": [\n";
  for (size_t i = 0; i < mutations.size(); ++i) {
    const auto& mutation = mutations[i];
    std::cout << indent << "  {\n";
    print_json_string_field("scope", mutation.scope, indent + "    ", true);
    print_json_string_field("ref", mutation.ref, indent + "    ", true);
    print_json_string_field("mode", mutation.mode, indent + "    ", false);
    std::cout << indent << "  }";
    if (i + 1 < mutations.size()) std::cout << ",";
    std::cout << "\n";
  }
  std::cout << indent << "]";
  if (comma) std::cout << ",";
  std::cout << "\n";
}

void print_expected_facts(const std::vector<std::string>& facts, const std::string& indent, bool comma) {
  std::cout << indent << "\"expected_facts\": [\n";
  for (size_t i = 0; i < facts.size(); ++i) {
    std::cout << indent << "  \"" << json_escape(facts[i]) << "\"";
    if (i + 1 < facts.size()) std::cout << ",";
    std::cout << "\n";
  }
  std::cout << indent << "]";
  if (comma) std::cout << ",";
  std::cout << "\n";
}

bool parse_gadget_arg(const Args& args, std::string& gizmo, std::string& gadget) {
  for (size_t i = 1; i < args.values.size(); ++i) {
    if (args.values[i] == "--gadget" && i + 2 < args.values.size()) {
      gizmo = args.values[i + 1];
      gadget = args.values[i + 2];
      return true;
    }
  }
  return false;
}

int print_status(const Args& args) {
  std::string gizmo = "lambdascript";
  std::string gadget = "core";
  parse_gadget_arg(args, gizmo, gadget);
  const auto target = make_gadget_target(gizmo, gadget);
  const CommandPlan plan{
    "status",
    "read-only",
    false,
    target,
    {
      AgentLane{"ed", "origin/gadget-agents/" + gizmo + "/" + gadget + "/ed", "unknown"},
      AgentLane{"edd", "origin/gadget-agents/" + gizmo + "/" + gadget + "/edd", "unknown"},
      AgentLane{"eddy", "origin/gadget-agents/" + gizmo + "/" + gadget + "/eddy", "unknown"}
    },
    {}
  };

  std::cout
    << "{\n"
    << "  \"format\": \"FORKS_CORE_STATUS_V1\",\n"
    << "  \"command\": \"" << plan.command << "\",\n"
    << "  \"mutation_scope\": \"" << plan.mutation_scope << "\",\n"
    << "  \"mutates\": false,\n"
    << "  \"implemented\": \"shape-only\",\n";
  print_gadget(plan.gadget, "  ", true);
  std::cout << "  \"agent_lanes\": [\n";
  for (size_t i = 0; i < plan.lanes.size(); ++i) {
    const auto& lane = plan.lanes[i];
    std::cout << "    {\n";
    print_json_string_field("agent", lane.agent, "      ", true);
    print_json_string_field("ref", lane.ref, "      ", true);
    print_json_string_field("relation", lane.relation, "      ", false);
    std::cout << "    }";
    if (i + 1 < plan.lanes.size()) std::cout << ",";
    std::cout << "\n";
  }
  std::cout << "  ],\n";
  print_expected_facts({
    "integration_ref",
    "agent_refs",
    "ahead_behind",
    "replay_ledger_entries",
    "expected_mutations"
  }, "  ", true);
  print_expected_mutations(plan.expected_mutations, "  ", false);
  std::cout << "}\n";
  return 0;
}

int audit_gadget(const Args& args) {
  std::string gizmo;
  std::string gadget;
  if (!parse_gadget_arg(args, gizmo, gadget)) {
    std::cerr << "audit requires --gadget <gizmo> <gadget>\n";
    return 1;
  }
  const auto target = make_gadget_target(gizmo, gadget);
  const CommandPlan plan{
    "audit",
    "read-only",
    false,
    target,
    {},
    {}
  };

  std::cout
    << "{\n"
    << "  \"format\": \"FORKS_CORE_AUDIT_V1\",\n"
    << "  \"command\": \"" << plan.command << "\",\n"
    << "  \"mutation_scope\": \"" << plan.mutation_scope << "\",\n"
    << "  \"mutates\": false,\n"
    << "  \"implemented\": \"shape-only\",\n";
  print_gadget(plan.gadget, "  ", true);
  print_expected_facts({
    "payload_presence",
    "latest_writer_per_path",
    "strict_mismatches",
    "advisory_mismatches",
    "materialisation_result"
  }, "  ", true);
  print_expected_mutations(plan.expected_mutations, "  ", false);
  std::cout << "}\n";
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
    return print_status(args);
  }
  if (command == "audit") {
    return audit_gadget(args);
  }

  std::cerr << "unsupported forks-core command in read-only scaffold: " << command << "\n";
  print_usage();
  return 1;
}
