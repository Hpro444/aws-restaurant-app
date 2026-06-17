import SignupForm from "./components/SignupForm";

import logo from "../../assets/Logo.png";
import image from "../../assets/signup/Image.png";

const SignupPage = () => {
  return (
    <div className="bg-[var(--color-bg-page)]">
      <div className="flex flex-col min-h-screen max-w-[1440px] mx-auto">
        <header className="pt-3 pl-10 pb-[18px]">
          <img alt="Green & Tasty" src={logo} />
        </header>
        <div className="grid grid-cols-2 gap-8 flex-1 max-w-[1360px] mx-auto pb-6">
          <div className="flex justify-center px-[84px] pb-[30px]">
            <div className="flex flex-col justify-center gap-8">
              <div>
                <p className="uppercase font-light text-sm text-[var(--color-text-primary)] leading-6">
                  Let's get you started!
                </p>
                <h2 className="font-medium text-2xl leading-10 text-[var(--color-text-primary)]">
                  Create An Account
                </h2>
              </div>
              <SignupForm />
            </div>
          </div>
          <div className="flex flex-col justify-center items-center gap-16 px-11">
            <p className="font-bold text-[80px] leading-none align-middle text-[var(--color-brand)]">
              Green <span className="text-[var(--color-black)]">& Tasty</span>
            </p>
            <img alt="Register" src={image} />
          </div>
        </div>
      </div>
    </div>
  );
};

export default SignupPage;
