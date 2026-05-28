import { Link } from "react-router-dom";

type BreadcrumbItem = {
  label: string;
  path?: string;
  isActive?: boolean;
};

type BreadcrumbProps = {
  items: BreadcrumbItem[];
};

const Breadcrumb = ({ items }: BreadcrumbProps) => {
  return (
    <section className="flex gap-2 mt-2 font-light text-[14px] leading-[24px] tracking-normal">
      {items.map((item, index) => (
        <div key={index} className="flex gap-2 items-center">
          {item.path && !item.isActive ? (
            <Link 
              to={item.path} 
              className="cursor-pointer hover:text-[var(--color-brand)] transition-colors"
            >
              {item.label}
            </Link>
          ) : (
            <span 
              className={`${
                item.isActive 
                  ? "font-medium text-[14px] leading-[24px]" 
                  : "cursor-pointer"
              }`}
            >
              {item.label}
            </span>
          )}
          {index < items.length - 1 && <span>{">"}</span>}
        </div>
      ))}
    </section>
  );
};

export default Breadcrumb;