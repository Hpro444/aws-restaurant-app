import close_icon from "../../../assets/close_icon.png";

const ReservationConfirmModal = () => {
  return (
    <div className="z-50 absolute top-6/12 left-6/12 transform -translate-x-1/2 -translate-y-1/2 flex flex-col w-[496px] rounded-[24px] gap-[40px] p-[24px] shadow-[0_0_10px_4px_#DADADAB2] bg-[#F7F7F7]">
      <div className="flex justify-between items-center">
        <h2 className="font-medium text-2xl leading-[40px] align-middle tracking-normal">
          Reservation Confirmed!
        </h2>
        <button>
          <img src={close_icon} alt="Close" />
        </button>
      </div>
      <div className="flex flex-col gap-3 font-light text-sm leading-[24px] tracking-normal align-middle">
        <p>
          Your table reservation at{" "}
          <span className="font-medium">Green & Tasty</span> for{" "}
          <span className="font-medium">10 people</span> on{" "}
          <span className="font-medium">Oct 14, 2024</span>, from{" "}
          <span className="font-medium">12:15 p.m.</span> to{" "}
          <span className="font-medium">1:45 p.m.</span> at{" "}
          <span className="font-medium">Table 1</span> has been successfully
          made.
        </p>
        <p>
          We look forward to welcoming you at{" "}
          <span className="font-medium">48 Rustaveli Avenue</span>.
        </p>
        <p>
          If you need to modify or cancel your reservation, you can do so up to
          30 min. before the reservation time.
        </p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <button className="rounded-[8px] py-2 border border-[#00ad0c] text-[#00ad0c] font-bold text-sm leading-[24px] tracking-normal text-center align-middle">
          Cancel Reservation
        </button>
        <button className="rounded-[8px] py-2 bg-[#00ad0c] text-white font-bold text-sm leading-[24px] tracking-normal text-center align-middle">
          Edit Reservation
        </button>
      </div>
    </div>
  );
};

export default ReservationConfirmModal;
