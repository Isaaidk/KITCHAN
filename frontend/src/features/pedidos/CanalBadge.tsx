import { infoCanal } from "./estadoUtils";

/** Chip con el nombre y el color de marca del canal (Uber Eats, Rappi, ...). */
export default function CanalBadge({ origen }: { origen: string }) {
  const { nombre, color } = infoCanal(origen);
  return (
    <span className="badge badge-dot" style={{ ["--badge-color" as string]: color }}>
      {nombre}
    </span>
  );
}
