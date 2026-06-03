const Layout = ({
  className,
  children,
}: {
  className?: string;
  children: React.ReactNode;
}) => {
  return (
    <>
      <div
        className={`px-10 pt-16 pb-15 flex flex-col gap-16 max-w-[1440px] mx-auto font-poppins ${className}`}
      >
        {children}
      </div>
    </>
  );
};

export default Layout;
