export const motion = {
  card: "transition-[transform,box-shadow,border-color] duration-200 hover:-translate-y-0.5 hover:shadow-card-hover motion-reduce:transition-none motion-reduce:hover:translate-y-0",
  button: "transition-[transform,background-color,border-color,color,box-shadow] duration-150 active:scale-[0.98] motion-reduce:transition-none motion-reduce:active:scale-100",
  panel: "animate-in fade-in slide-in-from-bottom-1 duration-150 motion-reduce:animate-none",
  modal: "animate-in fade-in zoom-in-95 duration-150 motion-reduce:animate-none",
  row: "transition-colors duration-150 hover:bg-muted/50 motion-reduce:transition-none",
};
