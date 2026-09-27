import { useMutation } from "@tanstack/react-query";
import { Download } from "lucide-react";
import { useState } from "react";

import { Alert, Button, Card, PageHeader, Select } from "@/design-system/components";
import { useSession } from "@/features/auth/session-store";
import { errorMessage } from "@/lib/api";
import { downloadAuthenticated } from "@/lib/download";

import { type ExportDataset, type ExportFormat, researchApi } from "../api";

const DATASETS: Record<ExportDataset, string> = {
  participants: "Participantes (pseudonimizados)",
  sessions: "Sesiones",
  interactions: "Interacciones (esquema de eventos C.19)",
  episodes: "Episodios",
  scaffold_events: "Decisiones de andamiaje y fading",
  state_history: "Historial del perfil dinámico (interpretación del sistema)",
  memos: "Mis memos",
  interviews: "Mis entrevistas",
};

export function ExportPage() {
  const { accessToken, user } = useSession();
  const [dataset, setDataset] = useState<ExportDataset>("interactions");
  const [format, setFormat] = useState<ExportFormat>("csv");
  const teacher = user?.role === "TEACHER";
  const allowed = teacher ? (["sessions", "interactions", "episodes"] as ExportDataset[]) : (Object.keys(DATASETS) as ExportDataset[]);
  const download = useMutation({ mutationFn: () => downloadAuthenticated(researchApi.exportUrl(dataset, format), accessToken, `${dataset}.${format}`) });

  return (
    <>
      <PageHeader eyebrow="Datos" title="Exportar" description="Solo datos en tu alcance, identificados por código. Cada exportación queda registrada en la auditoría." />
      <Card>
        <div className="ds-stack" style={{ maxWidth: 520 }}>
          <Select
            label="Conjunto de datos"
            value={dataset}
            onChange={(e) => {
              setDataset(e.target.value as ExportDataset);
            }}
          >
            {allowed.map((d) => (
              <option key={d} value={d}>
                {DATASETS[d]}
              </option>
            ))}
          </Select>
          <Select
            label="Formato"
            value={format}
            onChange={(e) => {
              setFormat(e.target.value as ExportFormat);
            }}
          >
            <option value="csv">CSV</option>
            <option value="json">JSON</option>
            <option value="jsonl">JSONL</option>
            <option value="xlsx">Excel (.xlsx)</option>
            <option value="pdf">PDF</option>
          </Select>
          {download.isError && <Alert tone="error">{errorMessage(download.error)}</Alert>}
          {download.isSuccess && <Alert tone="success">Descarga generada.</Alert>}
          <Button
            leadingIcon={<Download size={16} aria-hidden />}
            loading={download.isPending}
            onClick={() => {
              download.mutate();
            }}
          >
            Descargar
          </Button>
        </div>
      </Card>
    </>
  );
}
