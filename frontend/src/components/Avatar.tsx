interface AvatarProps {
  initials: string;
  src?: string;
  size?: "sm" | "md" | "lg";
}

const sizeClasses = {
  sm: "h-8 w-8 text-xs",
  md: "h-10 w-10 text-sm",
  lg: "h-12 w-12 text-base",
};

export function UserAvatar({ initials, src, size = "md" }: AvatarProps) {
  return (
    <div className={`${sizeClasses[size]} rounded-full bg-primary text-primary-foreground font-bold flex items-center justify-center overflow-hidden shrink-0`}>
      {src ? (
        <img src={src} alt="" className="h-full w-full object-cover" onError={(e) => { (e.target as HTMLImageElement).style.display = 'none'; }} />
      ) : (
        initials
      )}
    </div>
  );
}
