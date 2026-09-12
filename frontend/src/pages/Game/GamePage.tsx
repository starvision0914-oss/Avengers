export default function GamePage() {
  return (
    <iframe
      src={`http://${window.location.hostname}:8010/game/`}
      title="야구단 매니저"
      className="w-full h-[calc(100vh-3.5rem)] border-0"
    />
  );
}
