import CanalLogo from "../../shared/components/CanalLogo";
import { infoCanal } from "./estadoUtils";

/** Chip con el logo y el nombre del canal (Uber Eats, Rappi, ...). */
export default function CanalBadge({ origen }: { origen: string }) {
  const { nombre, color } = infoCanal(origen);
  return (
    <span
      className="badge"
      style={{ ["--badge-color" as string]: color, paddingLeft: 4, gap: 6 }}
    >
      <CanalLogo canal={origen} color={color} nombre={nombre} size={18} />
      {nombre}
    </span>
  );
}
