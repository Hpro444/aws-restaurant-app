import logo from "../../assets/Logo.png";
import image from "../../assets/signup/Image.png";
import LoginForm from "./components/LoginForm";

const LoginPage = () => {
  return (
    <div className="flex flex-col bg-[var(--color-background)] min-h-screen">
      <header className="pt-3 pl-10 pb-[18px]">
        <img alt="Green & Tasty" src={logo} />
      </header>
      <div className="grid grid-cols-2 gap-8 flex-1 max-w-[1360px] mx-auto pb-6">
        <div className="flex justify-center px-[84px] pb-[30px]">
          <div className="flex flex-col justify-center gap-8">
            <div>
              <p className="uppercase font-light text-sm text-[var(--color-text-primary)] leading-6">
                Welcome back
              </p>
              <h2 className="font-medium text-2xl leading-10 text-[var(--color-text-primary)]">
                Sign In to Your Account
              </h2>
            </div>
            <LoginForm />
          </div>
        </div>
        <div className="flex flex-col justify-center items-center gap-16 px-11">
          <p className="font-bold text-[80px] leading-none align-middle text-[var(--color-brand)]">
            Green <span className="text-black">& Tasty</span>
          </p>
          <img alt="Login" src={image} />
        </div>
      </div>
    </div>
  );
};

export default LoginPage;
