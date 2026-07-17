// PluginPauseRunButton — host-side wrapper for the paperclip-pause plugin's
// PauseRunButton sidebar slot. The plugin worker is responsible for
// actually toggling the global pause flag; this wrapper just looks up
// the registered sidebar slot component and renders it inline in the
// top bar (to the right of the version badge). When the plugin is not
// installed (e.g. paperclip upstream, paperclip-mods), this renders
// nothing and the bar behaves exactly as before.

import { PluginSlotOutlet } from "@/plugins/slots";
import { useCompany } from "../context/CompanyContext";

const PAUSE_SLOT_TYPE = "sidebar" as const;

export function PluginPauseRunButton() {
  const { selectedCompanyId, companies } = useCompany();
  const selectedCompany = companies.find((c) => c.id === selectedCompanyId) ?? null;

  return (
    <PluginSlotOutlet
      slotTypes={[PAUSE_SLOT_TYPE]}
      context={{
        companyId: selectedCompanyId,
        companyPrefix: selectedCompany?.issuePrefix ?? null,
        projectId: null,
        entityId: null,
        entityType: null,
        userId: null,
      }}
      missingBehavior="hidden"
    />
  );
}
