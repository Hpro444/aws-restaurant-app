import star_icon from "../../assets/restaurant/star-icon.png";
import type { Feedback } from "../../types/location";
import { formatDate } from "../../utils/reservationHelpers";

const FeedbackCard = ({ feedback }: { feedback: Feedback }) => {
  const rating = feedback.rate;

  const renderStars = (rating: number) => {
    return Array.from({ length: 5 }, (_, index) => (
      <span key={index}>
        <img
          src={star_icon}
          alt="Star"
          style={{
            opacity: index < rating ? 1 : 0.3,
          }}
        />
      </span>
    ));
  };

  return (
    <div className="flex flex-col shadow-[0px_0px_10px_4px_#DADADAB2] rounded-3xl">
      <div className="p-6 flex justify-between gap-3">
        <div className="w-[60px] h-[60px]">
          <img
            src={feedback.user_image_url}
            alt="User Avatar"
            className="rounded-[50%] object-cover w-full h-full"
          />
        </div>
        <div className="flex justify-between flex-1">
          <div className="font-medium text-[14px] leading-[24px] tracking-normal">
            <p>{feedback.user_name}</p>
            <p className="font-light text-[12px] leading-[16px]">
              {formatDate(feedback.date)}
            </p>
          </div>
          <p className="flex gap-1">{renderStars(rating)}</p>
        </div>
      </div>
      <div className="flex-1 px-6 pb-6">
        <p className="max-w-[268px] font-poppins font-light text-[14px] leading-[24px] tracking-normal">
          {feedback.feedback}
        </p>
      </div>
    </div>
  );
};

export default FeedbackCard;
