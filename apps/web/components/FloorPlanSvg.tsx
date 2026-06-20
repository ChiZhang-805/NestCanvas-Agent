import { FloorPlan, LayoutOption, Point } from "@/lib/types";

const roomFill: Record<string, string> = {
  living_room: "#d8e8de",
  dining_room: "#ead7bd",
  kitchen: "#ead7bd",
  master_bedroom: "#dfe5ef",
  bedroom: "#e9dfef",
  bathroom: "#cfe2ea"
};

const furnitureFill: Record<string, string> = {
  sofa: "#4f6f64",
  coffee_table: "#b65f45",
  tv_console: "#22312c",
  bookshelf: "#8f6548",
  toy_storage: "#536a9f",
  bed: "#536a9f",
  wardrobe: "#6b7b74",
  nightstand: "#b65f45",
  low_drawer: "#8f6548",
  dining_table: "#b65f45",
  counter: "#206d68",
  vanity: "#4f6f64",
  toilet: "#dfe5ef"
};

function bounds(points: Point[]) {
  const xs = points.map((point) => point[0]);
  const ys = points.map((point) => point[1]);
  return {
    minX: Math.min(...xs),
    minY: Math.min(...ys),
    maxX: Math.max(...xs),
    maxY: Math.max(...ys)
  };
}

function centroid(points: Point[]): Point {
  const open = points.slice(0, -1);
  const sum = open.reduce(
    (acc, point) => [acc[0] + point[0], acc[1] + point[1]] as Point,
    [0, 0]
  );
  return [sum[0] / open.length, sum[1] / open.length];
}

export function FloorPlanSvg({
  floorplan,
  option,
  compact = false
}: {
  floorplan: FloorPlan | null;
  option?: LayoutOption | null;
  compact?: boolean;
}) {
  if (!floorplan) {
    return (
      <div className="flex aspect-[4/3] items-center justify-center rounded-md border border-dashed border-ink/20 bg-white text-sm text-ink/60">
        FloorPlan JSON
      </div>
    );
  }

  const planBounds = bounds(floorplan.boundary);
  const scale = compact ? 58 : 82;
  const width = Math.max(1, (planBounds.maxX - planBounds.minX) * scale);
  const height = Math.max(1, (planBounds.maxY - planBounds.minY) * scale);

  const project = (point: Point): Point => [
    (point[0] - planBounds.minX) * scale,
    (planBounds.maxY - point[1]) * scale
  ];

  const polygonPoints = (points: Point[]) =>
    points.map(project).map((point) => point.join(",")).join(" ");

  return (
    <svg
      viewBox={`0 0 ${width} ${height}`}
      className="h-auto w-full rounded-md border border-ink/10 bg-white shadow-panel"
      role="img"
      aria-label="NestCanvas floor plan"
    >
      <rect width={width} height={height} fill="#ffffff" />
      <polygon
        points={polygonPoints(floorplan.boundary)}
        fill="#f6f3ea"
        stroke="#22312c"
        strokeWidth={3}
      />
      {floorplan.rooms.map((room) => {
        const [cx, cy] = project(centroid(room.polygon));
        return (
          <g key={room.id}>
            <polygon
              points={polygonPoints(room.polygon)}
              fill={roomFill[room.room_type] ?? "#edf0ed"}
              stroke="#22312c"
              strokeWidth={1.8}
            />
            {!compact && (
              <text
                x={cx}
                y={cy}
                textAnchor="middle"
                dominantBaseline="central"
                fill="#22312c"
                fontSize={13}
                fontWeight={600}
              >
                {room.room_type}
              </text>
            )}
          </g>
        );
      })}
      {floorplan.doors.map((door) => (
        <polygon
          key={door.id}
          points={polygonPoints(door.bbox)}
          fill="#ffffff"
          stroke="#b65f45"
          strokeWidth={2.2}
        />
      ))}
      {floorplan.windows.map((windowItem) => (
        <polygon
          key={windowItem.id}
          points={polygonPoints(windowItem.bbox)}
          fill="#dfe5ef"
          stroke="#536a9f"
          strokeWidth={2}
        />
      ))}
      {option?.furniture_items.map((item) => (
        <polygon
          key={item.id}
          points={polygonPoints(item.bbox)}
          fill={furnitureFill[item.category] ?? "#6b7b74"}
          fillOpacity={0.88}
          stroke="#ffffff"
          strokeWidth={1.6}
        />
      ))}
    </svg>
  );
}
