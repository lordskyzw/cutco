import { Inter } from "next/font/google";
import Head from "next/head";
import Button from "@/components/button";
import DollarInput from "@/components/input/dollar_input";
import PhoneNumberInput from "@/components/input/phone_number";
import axios, { AxiosError } from "axios";
import { FormEvent, FormEventHandler, useState } from "react";
import * as Tabs from "@radix-ui/react-tabs";
import Image from "next/image";

const inter = Inter({ subsets: ["latin"] });

const notificationMethods = [
  { id: "deposit", title: "Deposit" },
  { id: "withdraw", title: "Withdraw" },
];

export default function Home() {
  const [successData, setSuccessData] = useState(null);
  const [error, setError] = useState({
    message: "",
  });

  const onSubmit = async (e: any) => {
    e.preventDefault();
    const phone = e.target.phone.value;
    const amount = e.target.amount.value;

    console.log(e.target.transaction_type.value);

    const phone_formatted = ""
      .concat(phone)
      .split("")
      .filter((item) => !!item && item !== " ")
      .join("");

    axios
      .post("http://localhost:5000/tx", {
        phone_number: "0" + phone_formatted,
        amount,
        transaction_type: "deposit",
      })
      .then((res: any) => {
        setSuccessData(res.data);
      })
      .catch((err: AxiosError) => {
        if (err.status === 400) {
          setError({
            message: "Customer has insufficent balance: Current balance is: ",
          });
        }
        console.error(err);
      });
  };
  return (
    <main
      className={`flex h-screen w-screen flex-col items-center justify-center p-24 ${inter.className}`}
    >
      <Head>
        <title>CUT Coin</title>
      </Head>
      <div className=" rounded-xl border border-zinc-400/30 shadow-sm w-full max-w-md">
        <div className="flex gap-2 items-center px-8 py-4 border-b">
          <Image
            src="/coin.png"
            alt="cut-coin-logo"
            width={24}
            height={24}
            className="w-6 h-6 bg-zinc-400 rounded-full"
          />
          <h1 className="font-bold text-xl tracking-tight text-zinc-900">
            CUT Coin
          </h1>
        </div>
        <form onSubmit={onSubmit} className="space-y-8 p-8">
          <div className="space-y-4">
            <PhoneNumberInput name="phone" />
            <DollarInput name="amount" />
          </div>
          <div>
            <label className="text-base font-medium text-gray-900">
              Action
            </label>
            <p className="text-sm leading-5 text-gray-500">
              Which action do you want to perform?
            </p>
            <fieldset className="mt-4">
              <legend className="sr-only">Action</legend>
              <div className="space-y-4 sm:flex sm:items-center sm:space-y-0 sm:space-x-10">
                {notificationMethods.map((notificationMethod) => (
                  <label
                    htmlFor={notificationMethod.id}
                    key={notificationMethod.id}
                    className="flex items-center flex-1 border py-2 px-3 rounded-xl has-[:checked]:ring-blue-500 has-[:checked]:ring-2 has-[:checked]:text-blue-900 has-[:checked]:bg-blue-100 font-semibold"
                  >
                    <input
                      id={notificationMethod.id}
                      name="transaction_type"
                      type="radio"
                      className="focus:ring-blue-500 h-4 w-4 text-blue-600 border-gray-300"
                    />
                    <p className="ml-3 block text-sm">
                      {notificationMethod.title}
                    </p>
                  </label>
                ))}
              </div>
            </fieldset>
          </div>
          <Button className="w-full">Confirm</Button>
        </form>
      </div>
    </main>
  );
}
