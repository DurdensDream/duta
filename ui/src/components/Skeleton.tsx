export default function Skeleton({
  height,
  width,
  className,
}: {
  height?: number | string;
  width?: number | string;
  className?: string;
}) {
  return (
    <div
      className={className ? `skeleton ${className}` : "skeleton"}
      style={{ height, width }}
      aria-hidden="true"
    />
  );
}
