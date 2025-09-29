import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";

interface SearchBarProps {
  value: string;
  onChange: (e: React.ChangeEvent<HTMLInputElement>) => void;
  onSubmit: (e: React.FormEvent<HTMLFormElement>) => void;
}

export default function SearchBar({ value, onChange, onSubmit }: SearchBarProps) {
  return (
    <form onSubmit={onSubmit} className="w-full max-w-3xl mx-auto">
      <div className="relative group">
        <div className="absolute inset-0 bg-gradient-to-r from-blue-500/20 to-purple-500/20 rounded-2xl blur-xl opacity-0 group-hover:opacity-100 transition-opacity duration-500"></div>
        <div className="relative bg-card border border-border rounded-2xl p-1 shadow-lg backdrop-blur-sm">
          <div className="flex items-center">
            <div className="flex items-center pl-4 pr-2">
              <SearchIcon className="h-5 w-5 text-muted-foreground" />
            </div>
            <Input
              type="search"
              placeholder="법령, 판례, 법률 질문을 입력하세요..."
              className="flex-1 border-0 bg-transparent text-base placeholder:text-muted-foreground focus-visible:ring-0 focus-visible:ring-offset-0 h-12"
              value={value}
              onChange={onChange}
            />
            {value && (
              <Button
                type="submit"
                size="sm"
                className="mr-2 bg-primary hover:bg-primary/90 text-primary-foreground rounded-xl px-4 py-2"
              >
                <ArrowIcon className="h-4 w-4" />
              </Button>
            )}
          </div>
        </div>
      </div>

      {/* Search suggestions/shortcuts */}
      <div className="mt-4 flex flex-wrap gap-2 justify-center">
        <button
          type="button"
          className="px-3 py-1 text-xs bg-secondary text-secondary-foreground rounded-full hover:bg-secondary/80 transition-colors"
          onClick={() => onChange({ target: { value: "자본시장법" } } as React.ChangeEvent<HTMLInputElement>)}
        >
          자본시장법
        </button>
        <button
          type="button"
          className="px-3 py-1 text-xs bg-secondary text-secondary-foreground rounded-full hover:bg-secondary/80 transition-colors"
          onClick={() => onChange({ target: { value: "개인정보보호법" } } as React.ChangeEvent<HTMLInputElement>)}
        >
          개인정보보호법
        </button>
        <button
          type="button"
          className="px-3 py-1 text-xs bg-secondary text-secondary-foreground rounded-full hover:bg-secondary/80 transition-colors"
          onClick={() => onChange({ target: { value: "최신 판례" } } as React.ChangeEvent<HTMLInputElement>)}
        >
          최신 판례
        </button>
      </div>
    </form>
  );
}

function SearchIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="11" cy="11" r="8" />
      <path d="m21 21-4.3-4.3" />
    </svg>
  );
}

function ArrowIcon(props: React.SVGProps<SVGSVGElement>) {
  return (
    <svg
      {...props}
      xmlns="http://www.w3.org/2000/svg"
      width="24"
      height="24"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M5 12h14" />
      <path d="m12 5 7 7-7 7" />
    </svg>
  );
}
